"""Opaque, immutable Serato previews committed only through trusted-main confirmation."""

from __future__ import annotations

import copy
import hashlib
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from xfinaudio.exporting.serato_crate import (
    MAX_ANCHORED_CRATE_BYTES,
    SeratoExportPlan,
    rollback_serato_crate_write,
    validate_serato_crate_bytes,
    write_serato_crate,
)
from xfinaudio.exporting.serato_playlist_exporter import (
    SeratoLibrary,
    plan_copilot_variant_serato_playlist_export,
    plan_generated_serato_playlist_export,
    plan_metadata_missing_field_serato_export,
    plan_metadata_status_serato_export,
    plan_serato_playlist_export,
)
from xfinaudio.headless.common import BackendError
from xfinaudio.headless.serato_safety import (
    DirectoryIdentity,
    FileIdentity,
    backup_target,
    crate_name,
    directory_identity,
    file_identity,
    opaque_id,
    open_directory,
    target_state,
    volume_root,
)
from xfinaudio.headless.serato_source import ExportSource, load_source
from xfinaudio.quality.dj_readiness import validate_serato_round_trip

if TYPE_CHECKING:
    from xfinaudio.headless.backend import HeadlessBackend

LOGGER = logging.getLogger(__name__)
SERATO_FIELDS = {
    "serato.registerDestination": {"seratoRoot"},
    "serato.preview": {"source", "destinationId", "name"},
    "serato.confirmation": {"previewId"},
    "serato.commit": {"previewId", "confirmed"},
    "serato.receipt.resolve": {"receiptId"},
}


@dataclass(frozen=True)
class Destination:
    root: Path
    label: str
    lineage: tuple[DirectoryIdentity, ...]

    @property
    def folder(self) -> Path:
        return self.root / "Subcrates"


@dataclass(frozen=True)
class Preview:
    source: ExportSource
    destination: Destination
    source_volume: Path | None
    plan: SeratoExportPlan | None
    target: tuple[FileIdentity | None, str | None]
    summary: dict[str, Any]


class SeratoExporter:
    """One serialized backend command owner. Renderer never receives authority-bearing paths."""

    def __init__(self, backend: HeadlessBackend) -> None:
        self.backend = backend
        self.destinations: dict[str, Destination] = {}
        self.previews: dict[str, Preview] = {}
        self.receipts: dict[str, tuple[dict[str, Any], Preview, FileIdentity | None]] = {}
        self.completed: dict[str, str] = {}

    @staticmethod
    def _retain(mapping: dict, key: str, value: Any) -> None:
        if len(mapping) >= 128:
            raise BackendError("export_limit", "Restart the application before creating more export sessions")
        mapping[key] = value

    def execute(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        required = SERATO_FIELDS[method] - ({"name"} if method == "serato.preview" else set())
        if not required <= set(params):
            raise BackendError("invalid_params", "Missing export parameters")
        if method == "serato.registerDestination":
            return self._register(params["seratoRoot"])
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

    def _register(self, value: Any) -> dict[str, Any]:
        try:
            if not isinstance(value, str) or not value or len(value) > 4096 or "\x00" in value:
                raise OSError("Invalid directory")
            root = Path(value)
            if not root.is_absolute() or root.name != "_Serato_" or root.resolve(strict=True) != root:
                raise OSError("Select a canonical existing Serato directory")
            lineage = directory_identity(root / "Subcrates")
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
        if directory_identity(destination.folder) != destination.lineage:
            raise OSError("Selected destination changed")

    def _preview(self, params: dict[str, Any]) -> dict[str, Any]:
        name = crate_name(params["name"]) if "name" in params else None
        source = load_source(self.backend, params["source"])
        destination = self.destinations.get(opaque_id(params["destinationId"]))
        if destination is None:
            raise BackendError("invalid_destination", "Select a Serato destination first")
        blockers = list(source.blockers)
        plan, source_volume = None, None
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
                            target_path = destination.folder / f"{name}.crate"
                            plan = plan.model_copy(
                                update={
                                    "crate_name": name,
                                    "target_path": target_path,
                                    "backup_path": target_path.with_name(f"{target_path.name}.bak"),
                                }
                            )
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
                    if len(plan.crate_bytes) > MAX_ANCHORED_CRATE_BYTES:
                        raise OSError("Crate exceeds the supported byte limit")
                    crate_name(plan.crate_name)
                    if plan.target_path.parent != destination.folder:
                        raise OSError("Invalid target containment")
                    if not validate_serato_crate_bytes(plan.crate_bytes, plan.relative_paths).valid:
                        raise OSError("Invalid crate bytes")
                    if tuple(source_volume / path for path in plan.relative_paths) != source.paths:
                        blockers.append("A Serato track reference does not resolve to its exact scanned source")
                    target = target_state(plan.target_path)
                    plan = plan.model_copy(update={"backup_path": backup_target(plan.target_path)})
            self._destination_current(destination)
        except (OSError, ValueError, RuntimeError) as error:
            raise BackendError(
                "invalid_destination", "The Serato destination or crate cannot be used safely"
            ) from error
        if load_source(self.backend, source.selector).revision != source.revision:
            raise BackendError("stale_source", "The source changed; preview the export again")
        preview_id = str(uuid4())
        summary = {
            "previewId": preview_id,
            "sourceRevision": source.revision,
            "filename": plan.target_path.name if plan else f"{name or 'XfinAudio'}.crate",
            "destinationLabel": destination.label,
            "trackCount": len(source.paths),
            "readiness": "blocked" if blockers else source.readiness,
            "warnings": source.warnings,
            "blockers": blockers,
            "canCommit": not blockers and plan is not None,
            "tracks": source.tracks,
            "backup": {"required": target[0] is not None},
        }
        self._retain(self.previews, preview_id, Preview(source, destination, source_volume, plan, target, summary))
        return copy.deepcopy(summary)

    def _recheck(self, preview: Preview, *, target: bool = True) -> None:
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
            if target and (
                target_state(preview.plan.target_path) != preview.target
                or file_identity(preview.plan.backup_path) is not None
            ):
                raise OSError("Planned target or backup changed")
        except (OSError, RuntimeError) as error:
            raise BackendError("stale_destination", "The destination changed; preview the export again") from error

    def _commit(self, preview_id: str, preview: Preview) -> dict[str, Any]:
        self._recheck(preview)
        assert preview.plan is not None
        if len(self.receipts) >= 128:
            raise BackendError("export_limit", "Restart the application before creating more exports")
        failure_code = "export_failed"

        def guard() -> None:
            nonlocal failure_code
            try:
                self._recheck(preview, target=False)
            except BackendError as error:
                failure_code = error.code
                raise OSError("Export binding changed") from error

        try:
            with open_directory(preview.destination.folder) as (descriptor, lineage):
                if lineage != preview.destination.lineage:
                    raise BackendError("stale_destination", "The destination changed; preview the export again")
                result = write_serato_crate(
                    preview.plan,
                    confirm=True,
                    directory_fd=descriptor,
                    expected_target_identity=preview.target[0],
                    expected_target_digest=preview.target[1],
                    guard=guard,
                )
                published = os.stat(preview.plan.target_path.name, dir_fd=descriptor, follow_symlinks=False)
                identity = (published.st_dev, published.st_ino, published.st_mtime_ns, published.st_size)
                try:
                    guard()
                    if validate_serato_round_trip(preview.plan, volume_root=preview.source_volume).status != "ready":
                        raise OSError("Crate round-trip validation failed")
                    guard()
                except OSError:
                    rollback_serato_crate_write(result, directory_fd=descriptor, expected_target_identity=identity)
                    raise
        except OSError as error:
            LOGGER.exception("Confirmed Serato export failed")
            raise BackendError(
                failure_code, "The crate could not be exported safely; inspect local diagnostics before retrying"
            ) from error
        receipt_id = str(uuid4())
        receipt = {
            "receiptId": receipt_id,
            "filename": preview.plan.target_path.name,
            "destinationLabel": preview.destination.label,
            "trackCount": preview.plan.track_count,
            "validated": result.validated,
            "backupCreated": result.backup_path is not None,
        }
        self.receipts[receipt_id] = (receipt, preview, identity)
        self.completed[preview_id] = receipt_id
        return copy.deepcopy(receipt)
