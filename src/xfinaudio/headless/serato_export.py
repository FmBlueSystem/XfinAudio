"""Opaque, immutable Serato previews committed only through trusted-main confirmation."""

from __future__ import annotations

import copy
import hashlib
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast
from uuid import uuid4

from xfinaudio.exporting.serato_crate import (
    MAX_ANCHORED_CRATE_BYTES,
    SeratoExportPlan,
    SeratoWriteResult,
    plan_empty_serato_parent_crate,
    remove_created_serato_crate,
    rollback_serato_crate_write,
    validate_serato_crate_bytes,
    write_serato_crate,
)
from xfinaudio.exporting.serato_playlist_exporter import (
    SeratoCrateTreePlan,
    SeratoLibrary,
    nest_under_root_crate,
    parent_crate_names,
    plan_copilot_variant_serato_playlist_export,
    plan_generated_serato_playlist_export,
    plan_metadata_missing_field_serato_export,
    plan_metadata_status_serato_export,
    plan_serato_crate_tree,
    plan_serato_playlist_export,
    validate_segment_size,
)
from xfinaudio.headless.common import BackendError
from xfinaudio.headless.serato_discovery import suggest_destination
from xfinaudio.headless.serato_process import serato_is_running
from xfinaudio.headless.serato_safety import (
    DirectoryIdentity,
    FileIdentity,
    backup_target,
    crate_name,
    destination_identity,
    file_identity,
    opaque_id,
    open_destination,
    target_state,
    volume_root,
)
from xfinaudio.headless.serato_source import ExportSource, load_source, source_unchanged
from xfinaudio.quality.dj_readiness import validate_serato_round_trip

if TYPE_CHECKING:
    from xfinaudio.headless.backend import HeadlessBackend

LOGGER = logging.getLogger(__name__)
# Every crate of a tree is bounded like the source: the same 500 track references.
MAX_CRATE_TRACK_REFERENCES = 500
# The three split choices the export screen offers; an absent one is today's contract.
PreviewSplitMode = Literal["none", "every", "phases"]
PREVIEW_SPLIT_MODES: tuple[str, ...] = ("none", "every", "phases")
_SPLIT_MODE_ERROR = "split mode must be none, every or phases"
SERATO_FIELDS = {
    "serato.registerDestination": {"seratoRoot"},
    "serato.suggestDestination": set(),
    "serato.preview": {"source", "destinationId", "name", "segmentSize", "splitMode"},
    "serato.confirmation": {"previewId"},
    "serato.commit": {"previewId", "confirmed"},
    "serato.receipt.resolve": {"receiptId"},
}


@dataclass(frozen=True)
class Destination:
    """One authorized `_Serato_` folder.

    `lineage` binds the volume and `_Serato_` itself. The `Subcrates` folder inside it is
    deliberately not part of the binding: Serato recreates it, with new inode numbers,
    every time it rewrites its crates, so the leaf is re-proven structurally on each call
    (`destination_identity`) instead of being compared to a snapshot.
    """

    root: Path
    label: str
    lineage: tuple[DirectoryIdentity, ...]

    @property
    def folder(self) -> Path:
        return self.root / "Subcrates"


@dataclass(frozen=True)
class PreviewCrate:
    """One crate a preview approved, with the target state it bound."""

    plan: SeratoExportPlan
    target: tuple[FileIdentity | None, str | None]


@dataclass(frozen=True)
class Preview:
    source: ExportSource
    destination: Destination
    source_volume: Path | None
    plan: SeratoExportPlan | None
    target: tuple[FileIdentity | None, str | None]
    summary: dict[str, Any]
    parents: tuple[Path, ...] = ()
    # The whole tree of a split export, parent first; empty when the export writes one crate.
    crates: tuple[PreviewCrate, ...] = ()


def validate_preview_split_mode(value: object) -> PreviewSplitMode:
    """Refuse a split mode the options screen cannot offer: none, every or phases."""
    if not isinstance(value, str) or value not in PREVIEW_SPLIT_MODES:
        raise BackendError("invalid_params", _SPLIT_MODE_ERROR)
    return cast(PreviewSplitMode, value)


def _approved_crate(plan: SeratoExportPlan, destination: Destination) -> PreviewCrate:
    """Apply every crate rule to one planned crate and bind the target state it has now.

    The parent and each child go through the same name, containment, byte,
    track-reference and payload checks: a tree is no weaker than a single crate.
    """
    if len(plan.crate_bytes) > MAX_ANCHORED_CRATE_BYTES:
        raise OSError("Crate exceeds the supported byte limit")
    crate_name(plan.crate_name)
    if plan.target_path.parent != destination.folder:
        raise OSError("Invalid target containment")
    if plan.track_count > MAX_CRATE_TRACK_REFERENCES:
        raise OSError("Crate exceeds the supported track-reference limit")
    if not validate_serato_crate_bytes(plan.crate_bytes, plan.relative_paths).valid:
        raise OSError("Invalid crate bytes")
    target = target_state(plan.target_path)
    return PreviewCrate(plan.model_copy(update={"backup_path": backup_target(plan.target_path)}), target)


def _missing_parent_crates(plan: SeratoExportPlan, destination: Destination) -> tuple[Path, ...]:
    """Ancestors the child needs that are missing now, outermost first, under the child's checks."""
    missing: list[Path] = []
    for name in parent_crate_names(plan.target_path.stem):
        # An ancestor name follows exactly the rules of the child name it is derived from.
        crate_name(name)
        path = destination.folder / f"{name}.crate"
        if path.parent != destination.folder:
            raise OSError("Invalid parent containment")
        # A symlink or any other non-regular file at an ancestor path is refused like the child.
        if file_identity(path) is None:
            missing.append(path)
    return tuple(missing)


def _create_parent_crates(
    parents: tuple[Path, ...], descriptor: int, guard: Callable[[], None], created: list[tuple[Path, FileIdentity]]
) -> None:
    """Create the ancestors still missing, outermost first, never replacing one that appeared.

    Each parent reuses the child's anchored writer: an arrival after the existence
    check fails the exclusive publication instead of becoming an overwrite. Created
    parents are recorded as they land so a later failure can remove exactly them.
    """
    for path in parents:
        if file_identity(path) is not None:
            continue  # it exists now: an existing ancestor is never modified, replaced or backed up
        write_serato_crate(
            plan_empty_serato_parent_crate(path),
            confirm=True,
            directory_fd=descriptor,
            expected_target_identity=None,
            guard=guard,
        )
        published = file_identity(path)
        assert published is not None
        created.append((path, published))


def _remove_created_parent_crates(created: list[tuple[Path, FileIdentity]], descriptor: int) -> None:
    """Remove only the ancestors this commit created, newest first, while each is unchanged."""
    for path, identity in reversed(created):
        try:
            remove_created_serato_crate(path, identity, directory_fd=descriptor)
        except OSError:
            LOGGER.warning("Retained the parent crate this export created: %s", path, exc_info=True)


class SeratoExporter:
    """One serialized backend command owner. Renderer never receives authority-bearing paths."""

    def __init__(self, backend: HeadlessBackend) -> None:
        self.backend = backend
        self.destinations: dict[str, Destination] = {}
        self.previews: dict[str, Preview] = {}
        self.receipts: dict[str, tuple[dict[str, Any], Preview, FileIdentity | None]] = {}
        self.completed: dict[str, str] = {}
        # Serato rewrites its folder when it quits, deleting crates written while it ran.
        self.serato_running: Callable[[], bool] = serato_is_running

    @staticmethod
    def _retain(mapping: dict, key: str, value: Any) -> None:
        if len(mapping) >= 128:
            raise BackendError("export_limit", "Restart the application before creating more export sessions")
        mapping[key] = value

    def execute(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        optional = {"name", "segmentSize", "splitMode"} if method == "serato.preview" else set()
        required = SERATO_FIELDS[method] - optional
        if not required <= set(params):
            raise BackendError("invalid_params", "Missing export parameters")
        if method == "serato.registerDestination":
            return self._register(params["seratoRoot"])
        if method == "serato.suggestDestination":
            return self._suggest()
        if method == "serato.preview":
            return self._preview(params)
        if method == "serato.receipt.resolve":
            receipt_id = opaque_id(params["receiptId"])
            entry = self.receipts.get(receipt_id)
            if entry is None:
                raise BackendError("not_found", "Export receipt was not found")
            _, preview, expected = entry
            assert preview.plan is not None
            try:
                self._destination_current(preview.destination)
                if target_state(preview.plan.target_path) != (
                    expected,
                    hashlib.sha256(preview.plan.crate_bytes).hexdigest(),
                ):
                    raise OSError("Receipt target changed")
            except OSError as error:
                raise BackendError("stale_destination", "The exported crate moved or changed") from error
            return {"path": str(preview.plan.target_path)}
        preview_id = opaque_id(params["previewId"])
        preview = self.previews.get(preview_id)
        if preview is None:
            raise BackendError("stale_preview", "Preview the export again")
        if method == "serato.confirmation":
            if preview_id not in self.completed:
                self._recheck(preview)
            return copy.deepcopy(preview.summary)
        if params.get("confirmed") is not True:
            raise BackendError("confirmation_required", "Confirm the Serato export first")
        if preview_id in self.completed:
            return copy.deepcopy(self.receipts[self.completed[preview_id]][0])
        return self._commit(preview_id, preview)

    def _suggest(self) -> dict[str, Any]:
        """Best-effort `_Serato_` folder so the export needs no folder picker."""
        suggestion = suggest_destination(self.backend.roots, home=Path.home())
        return {"suggestion": None if suggestion is None else str(suggestion)}

    def _register(self, value: Any) -> dict[str, Any]:
        try:
            if not isinstance(value, str) or not value or len(value) > 4096 or "\x00" in value:
                raise OSError("Invalid directory")
            root = Path(value)
            if not root.is_absolute() or root.name != "_Serato_" or root.resolve(strict=True) != root:
                raise OSError("Select a canonical existing Serato directory")
            lineage = destination_identity(root)
        except (OSError, ValueError, RuntimeError) as error:
            raise BackendError(
                "invalid_destination", "Choose an existing _Serato_ folder containing Subcrates"
            ) from error
        label = "_Serato_ · " + "".join(char for char in root.parent.name if char.isprintable())[:80]
        destination_id = str(uuid4())
        self._retain(self.destinations, destination_id, Destination(root, label, lineage))
        return {"destinationId": destination_id, "label": label}

    @staticmethod
    def _destination_current(destination: Destination) -> None:
        if destination_identity(destination.root) != destination.lineage:
            raise OSError("Selected destination changed")

    def _preview(self, params: dict[str, Any]) -> dict[str, Any]:
        # An absent or empty name means the app names the crate: a generated set is named
        # from its strategy and the export date, inside the destination folder it writes to.
        name = crate_name(params["name"]) if params.get("name") else None
        # S4: the screen splits by segments, by the set's own energy phases, or not at all.
        # An absent mode is today's contract: the tramo size alone decides.
        split_mode: PreviewSplitMode | None = None
        if params.get("splitMode") is not None:
            split_mode = validate_preview_split_mode(params["splitMode"])
        # A split size is only present when the DJ chose one on the options screen; absent
        # or null keeps today's single crate. An invalid size is refused before any work.
        segment_size = None
        if params.get("segmentSize") is not None and split_mode != "phases":
            # A phase split owes nothing to the tramo size the screen still holds (S4).
            try:
                segment_size = validate_segment_size(params["segmentSize"])
            except ValueError as error:
                raise BackendError("invalid_params", str(error)) from error
        # A metadata worklist keeps its own naming: it is a worklist, not a set, so neither
        # a tramo size nor an energy split applies to it.
        worklist = isinstance(params["source"], dict) and params["source"].get("kind") == "metadata"
        if worklist and segment_size is not None:
            raise BackendError("invalid_params", "Segment size applies to a set export, not a metadata worklist")
        if worklist and split_mode == "phases":
            raise BackendError("invalid_params", "Energy phases apply to a set export, not a metadata worklist")
        source = load_source(self.backend, params["source"])
        destination = self.destinations.get(opaque_id(params["destinationId"]))
        if destination is None:
            # An id belongs to this process. A restart keeps no ids, so the shell must
            # detect the folder again instead of asking the user for one.
            raise BackendError("unknown_destination", "Select a Serato destination first")
        blockers = list(source.blockers)
        plan, source_volume = None, None
        tree: SeratoCrateTreePlan | None = None
        crates: tuple[PreviewCrate, ...] = ()
        parents: tuple[Path, ...] = ()
        target: tuple[FileIdentity | None, str | None] = (None, None)
        try:
            self._destination_current(destination)
            if not blockers and (source.recommendation is not None or source.metadata_records is not None):
                volumes = {volume_root(path) for path in source.paths}
                if len(volumes) != 1 or volume_root(destination.root) not in volumes:
                    blockers.append("All tracks and the selected Serato folder must belong to the same source volume")
                else:
                    source_volume = next(iter(volumes))
                    library = SeratoLibrary(serato_folder=destination.root, volume_root=source_volume)
                    if source.metadata_records is not None:
                        if source.selector["missingField"] is not None:
                            plan = plan_metadata_missing_field_serato_export(
                                source.metadata_records, source.selector["missingField"], library
                            )
                        else:
                            plan = plan_metadata_status_serato_export(
                                source.metadata_records, source.selector["status"], library
                            )
                        if name is not None:
                            # A typed name is a set's name, not a worklist leaf: it lives
                            # under the XfinAudio parent crate like every other typed name.
                            typed_name = nest_under_root_crate(name)
                            target_path = destination.folder / f"{typed_name}.crate"
                            plan = plan.model_copy(
                                update={
                                    "crate_name": typed_name,
                                    "target_path": target_path,
                                    "backup_path": target_path.with_name(f"{target_path.name}.bak"),
                                }
                            )
                    elif split_mode == "phases":
                        # One confirmation covers the tree: the parent with every track, then
                        # one child per energy phase of the set in the same reviewed order,
                        # or the parent alone with the reason when it has no phases (S4, S5).
                        assert source.recommendation is not None
                        tree = plan_serato_crate_tree(
                            source.recommendation, library, crate_name=name, split_mode="phases"
                        )
                        plan = tree.parent
                    elif segment_size is not None and split_mode != "none":
                        # One confirmation covers the tree: the parent with every track,
                        # then one child per segment in the same reviewed order.
                        assert source.recommendation is not None
                        tree = plan_serato_crate_tree(
                            source.recommendation, library, crate_name=name, segment_size=segment_size
                        )
                        plan = tree.parent
                    elif name is not None:
                        assert source.recommendation is not None
                        plan = plan_serato_playlist_export(name, source.recommendation, library)
                    elif source.variant is not None:
                        assert source.recommendation is not None
                        plan = plan_copilot_variant_serato_playlist_export(
                            source.variant, source.recommendation, library
                        )
                    else:
                        assert source.recommendation is not None
                        plan = plan_generated_serato_playlist_export(source.recommendation, library)
                    assert plan is not None
                    planned = tree.plans if tree is not None else (plan,)
                    crates = tuple(_approved_crate(crate, destination) for crate in planned)
                    plan, target = crates[0].plan, crates[0].target
                    if tuple(source_volume / path for path in plan.relative_paths) != source.paths:
                        blockers.append("A Serato track reference does not resolve to its exact scanned source")
                    parents = _missing_parent_crates(plan, destination)
            self._destination_current(destination)
        except (OSError, ValueError, RuntimeError) as error:
            raise BackendError(
                "invalid_destination", "The Serato destination or crate cannot be used safely"
            ) from error
        if load_source(self.backend, source.selector).revision != source.revision:
            raise BackendError("stale_source", "The source changed; preview the export again")
        preview_id = str(uuid4())
        if plan is not None:
            filename = plan.target_path.name
        elif name is not None:
            # A blocked preview still names the crate that export would write.
            filename = f"{nest_under_root_crate(name)}.crate"
        else:
            filename = "XfinAudio.crate"
        summary: dict[str, Any] = {
            "previewId": preview_id,
            "sourceRevision": source.revision,
            "filename": filename,
            "destinationLabel": destination.label,
            "trackCount": len(source.paths),
            "readiness": "blocked" if blockers else source.readiness,
            "warnings": source.warnings,
            "blockers": blockers,
            "canCommit": not blockers and plan is not None,
            "tracks": source.tracks,
            "parentsToCreate": [path.stem for path in parents],
            "backup": {"required": any(crate.target[0] is not None for crate in crates)},
        }
        if (segment_size is not None and split_mode != "none") or (tree is not None and tree.children):
            # A split export names every crate to create or replace, parent first.
            summary["crates"] = [
                {
                    "name": crate.plan.target_path.name,
                    "trackCount": crate.plan.track_count,
                    "action": "replace" if crate.target[0] is not None else "create",
                }
                for crate in crates
            ]
        if tree is not None and tree.phase_reason is not None:
            # S5: no phases were invented, the parent is exported alone and the preview says why.
            summary["phaseReason"] = tree.phase_reason
        self._retain(
            self.previews,
            preview_id,
            Preview(source, destination, source_volume, plan, target, summary, parents, crates),
        )
        return copy.deepcopy(summary)

    @staticmethod
    def _planned_crates(preview: Preview) -> tuple[PreviewCrate, ...]:
        """Every crate the preview approved: the parent first, then its children in order."""
        if preview.crates:
            return preview.crates
        assert preview.plan is not None
        return (PreviewCrate(preview.plan, preview.target),)

    def _recheck(self, preview: Preview) -> ExportSource:
        """Reload and re-verify the whole source and every planned target once.

        This is the one full verification a confirmed export makes: the returned source is
        the binding every later guard compares against, without reloading anything.
        """
        if not preview.summary["canCommit"] or preview.plan is None:
            raise BackendError("blocked_export", "Resolve export blockers before confirming")
        try:
            fresh = load_source(self.backend, preview.source.selector)
        except BackendError as error:
            raise BackendError("stale_source", "The source changed; preview the export again") from error
        if fresh.revision != preview.source.revision or fresh.readiness == "blocked":
            raise BackendError("stale_source", "The source changed; preview the export again")
        try:
            self._destination_current(preview.destination)
            # Every crate of the tree keeps the stale-preview rule of a single crate.
            for crate in self._planned_crates(preview):
                if (
                    target_state(crate.plan.target_path) != crate.target
                    or file_identity(crate.plan.backup_path) is not None
                ):
                    raise OSError("Planned target or backup changed")
        except (OSError, RuntimeError) as error:
            raise BackendError("stale_destination", "The destination changed; preview the export again") from error
        return fresh

    @staticmethod
    def _guard_binding(preview: Preview, verified: ExportSource) -> None:
        """The guard every crate write runs: destination lineage plus a cheap source check.

        The whole source is verified once, before the first write of the tree, and `verified`
        is that binding. What remains per write is the destination lineage and the stat
        identity of every scanned track, because a full reload cannot change what a confirmed
        tree writes: each crate's bytes and target identity were bound at preview time, the
        writer re-checks them itself, and this backend serializes one command at a time, so
        no selector or catalogue edit can land between two crates of the same commit.
        Reloading per crate cost ~30 s for a five-crate tree on an external drive (S3).
        """
        try:
            SeratoExporter._destination_current(preview.destination)
        except (OSError, RuntimeError) as error:
            raise BackendError("stale_destination", "The destination changed; preview the export again") from error
        if not source_unchanged(verified):
            raise BackendError("stale_source", "The source changed; preview the export again")

    @staticmethod
    def _roll_back_tree(
        written: list[tuple[SeratoWriteResult, FileIdentity]],
        created: list[tuple[Path, FileIdentity]],
        descriptor: int,
    ) -> None:
        """Undo one failed tree export in reverse: crates this export wrote, then its ancestors.

        A crate that cannot be restored is kept and logged, so every other crate of the
        tree is still put back and the DJ is never told more than the folder shows.
        """
        for result, identity in reversed(written):
            try:
                rollback_serato_crate_write(result, directory_fd=descriptor, expected_target_identity=identity)
            except OSError:
                LOGGER.warning("Retained the Serato crate this export wrote: %s", result.written_path, exc_info=True)
        _remove_created_parent_crates(created, descriptor)

    def _commit(self, preview_id: str, preview: Preview) -> dict[str, Any]:
        # One full source and target verification for the whole tree, inside this commit.
        verified = self._recheck(preview)
        assert preview.plan is not None
        if len(self.receipts) >= 128:
            raise BackendError("export_limit", "Restart the application before creating more exports")
        if self.serato_running():
            raise BackendError(
                "serato_running", "Close Serato DJ before exporting; it rewrites its crates when it quits"
            )
        failure_code = "export_failed"
        # The parent first, then its children in order: one confirmation, one destination.
        crates = self._planned_crates(preview)
        written: list[tuple[SeratoWriteResult, FileIdentity]] = []

        def guard() -> None:
            nonlocal failure_code
            try:
                self._guard_binding(preview, verified)
            except BackendError as error:
                failure_code = error.code
                raise OSError("Export binding changed") from error

        created: list[tuple[Path, FileIdentity]] = []
        try:
            with open_destination(preview.destination.root) as (descriptor, lineage, folder_device):
                if lineage != preview.destination.lineage or folder_device != lineage[-1][0]:
                    raise BackendError("stale_destination", "The destination changed; preview the export again")
                try:
                    _create_parent_crates(preview.parents, descriptor, guard, created)
                    for crate in crates:
                        result = write_serato_crate(
                            crate.plan,
                            confirm=True,
                            directory_fd=descriptor,
                            expected_target_identity=crate.target[0],
                            expected_target_digest=crate.target[1],
                            guard=guard,
                        )
                        published = os.stat(crate.plan.target_path.name, dir_fd=descriptor, follow_symlinks=False)
                        identity = (published.st_dev, published.st_ino, published.st_mtime_ns, published.st_size)
                        written.append((result, identity))
                        guard()
                        round_trip = validate_serato_round_trip(crate.plan, volume_root=preview.source_volume)
                        if round_trip.status != "ready":
                            raise OSError("Crate round-trip validation failed")
                        guard()
                except OSError:
                    # All or nothing: a failed commit leaves the folder as it found it, so
                    # every crate this export wrote goes back and the ancestors it created go.
                    self._roll_back_tree(written, created, descriptor)
                    raise
        except OSError as error:
            LOGGER.exception("Confirmed Serato export failed")
            raise BackendError(
                failure_code, "The crate could not be exported safely; inspect local diagnostics before retrying"
            ) from error
        receipt_id = str(uuid4())
        receipt: dict[str, Any] = {
            "receiptId": receipt_id,
            "filename": preview.plan.target_path.name,
            "destinationLabel": preview.destination.label,
            "trackCount": preview.plan.track_count,
            "validated": all(result.validated for result, _identity in written),
            "backupCreated": any(result.backup_path is not None for result, _identity in written),
            "parentsCreated": [path.stem for path, _identity in created],
        }
        if "crates" in preview.summary:
            # A split export names every crate it wrote; the parent stays `filename` so
            # «Mostrar en Finder» and the receipt path resolve exactly as before.
            receipt["files"] = [
                {"name": crate.plan.target_path.name, "trackCount": crate.plan.track_count} for crate in crates
            ]
        self.receipts[receipt_id] = (receipt, preview, written[0][1])
        self.completed[preview_id] = receipt_id
        return copy.deepcopy(receipt)
