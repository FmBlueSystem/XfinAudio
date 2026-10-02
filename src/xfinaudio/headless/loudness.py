"""Explicit, bounded loudness runs using the original engine and completion services."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

from xfinaudio.audio.loudness import FfmpegLoudnessAdapter, LoudnessStatus, is_complete_measurement
from xfinaudio.audio.loudness_completion import LoudnessAnalysisPort, LoudnessCompletionService
from xfinaudio.audio.loudness_runtime import probe_engine_fingerprint, resolve_ffmpeg
from xfinaudio.headless.cancellation import JobCancellationToken
from xfinaudio.headless.common import BackendError, _inside, _public_track
from xfinaudio.headless.loudness_write import BoundLoudnessWriter, SourceBinding, bind_source
from xfinaudio.headless.serato_safety import opaque_id
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.scan_service import ScanCancellationToken

if TYPE_CHECKING:
    from xfinaudio.headless.backend import HeadlessBackend

LOGGER = logging.getLogger(__name__)

LOUDNESS_FIELDS = {
    "loudness.status": set(),
    "loudness.settings.update": {"revision", "enabled", "targetLufs", "toleranceLu"},
    "loudness.preview": {"trackIds", "force"},
    "loudness.confirmation": {"previewId"},
    "loudness.run": {"previewId", "confirmed"},
}


@dataclass(frozen=True)
class Engine:
    analyzer: LoudnessAnalysisPort
    fingerprint: str


def create_engine() -> Engine | None:
    executable = resolve_ffmpeg()
    if executable is None:
        return None
    fingerprint = probe_engine_fingerprint(executable)
    if fingerprint is None:
        raise OSError("FFmpeg version probe failed")
    adapter = FfmpegLoudnessAdapter(executable, engine_fingerprint=fingerprint)
    adapter.preflight()
    return Engine(adapter, fingerprint)


@dataclass(frozen=True)
class LoudnessPreview:
    id: str
    revision: str
    records: tuple[TrackRecord, ...]
    bindings: tuple[tuple[str, SourceBinding], ...]
    force: bool


class BoundAnalyzer:
    def __init__(self, engine: Engine, writer: BoundLoudnessWriter, token: ScanCancellationToken) -> None:
        self.engine, self.writer, self.token = engine, writer, token

    def analyze(self, path: Path, *, duration_seconds: float):
        if self.token.is_cancelled:
            raise OSError("Loudness cancelled")
        self.writer.ensure_current(path)
        profile = self.engine.analyzer.analyze(path, duration_seconds=duration_seconds)
        self.writer.ensure_current(path)
        if self.token.is_cancelled:
            raise OSError("Loudness cancelled")
        return profile

    def cancel(self) -> None:
        if cancel := getattr(self.engine.analyzer, "cancel", None):
            cancel()


class OwnedWriteSuppressor:
    def __init__(self, records: tuple[TrackRecord, ...], emit: Any) -> None:
        self.ids = {record.path: _public_track(record)["id"] for record in records}
        self.emit = emit

    def suppress_paths(self, paths: Iterable[Path], *, duration_seconds: float) -> None:
        ids = [self.ids[str(path)] for path in paths if str(path) in self.ids]
        if ids:
            self.emit({"phase": "loudness_write", "trackIds": ids})


class LoudnessWorkflow:
    def __init__(self, backend: HeadlessBackend) -> None:
        self.backend = backend
        self.engine: Engine | None = None
        self.probed = False
        self.reason = "missing_engine"
        self.preview: LoudnessPreview | None = None
        self.receipts: dict[str, dict[str, Any]] = {}

    def invalidate(self) -> None:
        self.preview = None

    def _engine(self) -> Engine | None:
        if not self.probed:
            self.probed = True
            try:
                self.engine = create_engine()
                self.reason = "ready" if self.engine else "missing_engine"
            except (OSError, ValueError, RuntimeError):
                self.reason = "failed_engine"
        return self.engine

    def status(self) -> dict[str, Any]:
        settings = self.backend.preferences.get_loudness()
        engine = self._engine()
        records = self.backend._records()
        tracks = []
        for record in records:
            profile = record.loudness_profile
            if profile is not None:
                try:
                    binding = self._bind(record)
                    if (profile.source_mtime_ns, profile.source_size_bytes) != (binding[4], binding[3]):
                        profile = None
                except OSError:
                    profile = None
            tracks.append(
                {
                    "track": _public_track(record),
                    "state": profile.status.value if profile else "unmeasured",
                    "complete": bool(profile and is_complete_measurement(profile)),
                    "lufs": profile.lufs_integrated if profile else None,
                    "lra": profile.loudness_range_lra if profile else None,
                    "truePeak": profile.true_peak_dbtp if profile else None,
                }
            )
        return {
            **settings,
            "available": engine is not None,
            "reason": self.reason,
            "totalTracks": len(tracks),
            "tracks": tracks,
        }

    def execute(self, method: str, params: dict[str, Any], token: ScanCancellationToken, emit: Any) -> dict[str, Any]:
        if set(params) != LOUDNESS_FIELDS[method]:
            raise BackendError("invalid_params", "Missing or unexpected loudness fields")
        if method == "loudness.status":
            return self.status()
        if method == "loudness.settings.update":
            self.backend.preferences.update_loudness(params)
            self.invalidate()
            return self.status()
        if method == "loudness.preview":
            return self._prepare(params)
        preview_id = opaque_id(params["previewId"])
        if method == "loudness.run" and params["confirmed"] is not True:
            raise BackendError("confirmation_required", "Native loudness confirmation is required")
        if method == "loudness.run" and preview_id in self.receipts:
            return self.receipts[preview_id]
        preview = self._current(preview_id)
        if method == "loudness.confirmation":
            return {
                **self._public_preview(preview),
                "folders": sorted({str(Path(r.path).parent) for r in preview.records}),
                "backupDirectory": str(self.backend.data_dir / "loudness-backups"),
            }
        return self._run(preview, token, emit)

    def _prepare(self, params: dict[str, Any]) -> dict[str, Any]:
        ids, force = params["trackIds"], params["force"]
        if (
            not isinstance(ids, list)
            or not 1 <= len(ids) <= 500
            or any(not isinstance(value, str) for value in ids)
            or len(set(ids)) != len(ids)
            or type(force) is not bool
            or (force and len(ids) != 1)
        ):
            raise BackendError("invalid_params", "Choose 1–500 unique tracks; reanalysis requires one track")
        settings = self._enabled()
        known = {_public_track(record)["id"]: record for record in self.backend._records()}
        if any(value not in known for value in ids):
            raise BackendError("invalid_params", "Choose tracks from the authorized library")
        records = tuple(known[value] for value in ids)
        scanned = self.backend.repository.load_scan_file_identities(record.path for record in records)
        try:
            bindings = tuple((record.path, self._bind(record)) for record in records)
            if any(scanned.get(path) != (binding[4], binding[3]) for path, binding in bindings):
                raise OSError("Scanned metadata is stale")
        except OSError as error:
            raise BackendError("stale_loudness", "Selected sources changed; rescan and preview again") from error
        self.preview = LoudnessPreview(str(uuid4()), settings["revision"], records, bindings, force)
        return self._public_preview(self.preview)

    def _bind(self, record: TrackRecord) -> SourceBinding:
        path = Path(record.path)
        if not any(_inside(path, root) for root in self.backend.roots):
            raise OSError("Source escaped its authorized library")
        return bind_source(path)

    def _enabled(self) -> dict[str, Any]:
        settings = self.backend.preferences.get_loudness()
        if not settings["enabled"]:
            raise BackendError("loudness_disabled", "Loudness analysis and automatic tag writing are disabled")
        if self._engine() is None:
            raise BackendError("loudness_unavailable", "The loudness engine is unavailable")
        return settings

    def _current(self, preview_id: str) -> LoudnessPreview:
        preview = self.preview
        if preview is None or preview.id != preview_id or self._enabled()["revision"] != preview.revision:
            raise BackendError("stale_loudness", "Loudness scope or settings changed; preview again")
        try:
            if tuple((record.path, self._bind(record)) for record in preview.records) != preview.bindings:
                raise OSError("Source changed")
        except OSError as error:
            raise BackendError("stale_loudness", "Selected sources changed; rescan and preview again") from error
        return preview

    @staticmethod
    def _public_preview(preview: LoudnessPreview) -> dict[str, Any]:
        return {
            "previewId": preview.id,
            "trackCount": len(preview.records),
            "backupBytes": sum(cast(int, binding[3]) for _, binding in preview.bindings),
            "force": preview.force,
            "tracks": [_public_track(record) for record in preview.records],
            "replaceComments": True,
        }

    def _run(self, preview: LoudnessPreview, token: ScanCancellationToken, emit: Any) -> dict[str, Any]:
        assert self.engine is not None
        prior_status = self.status()
        self.invalidate()
        self.backend.invalidate_review()
        self.backend.editor.invalidate()
        writer = BoundLoudnessWriter(self.backend.data_dir, dict(preview.bindings))
        analyzer = BoundAnalyzer(self.engine, writer, token)
        service = LoudnessCompletionService(
            analyzer,
            engine_fingerprint=self.engine.fingerprint,
            tag_writer=writer,
            path_suppressor=OwnedWriteSuppressor(preview.records, emit),
        )
        remove = token.subscribe(service.cancel) if isinstance(token, JobCancellationToken) else lambda: None
        profiles = {}
        interrupted = False
        try:
            if not token.is_cancelled:
                service.complete(
                    preview.records,
                    self.backend.repository,
                    force_reanalyze=preview.force,
                    on_result=lambda path, profile: profiles.__setitem__(path, profile),
                    on_progress=lambda completed, total: emit(
                        {"phase": "loudness", "processedCount": completed, "totalCount": total}
                    ),
                )
        except Exception:
            LOGGER.exception("Loudness run interrupted; original-byte backups are retained")
            interrupted = True
        finally:
            remove()
        failures = {LoudnessStatus.TRANSIENT_FAILURE, LoudnessStatus.UNMEASURABLE, LoudnessStatus.UNSUPPORTED}
        unchanged = max(
            writer.unchanged_count, sum(p.status not in failures for p in profiles.values()) - writer.changed_count
        )
        remaining = max(0, len(preview.records) - writer.changed_count - unchanged)
        failure_count = min(
            remaining,
            remaining
            if interrupted
            else max(writer.failed_count, sum(p.status in failures for p in profiles.values())),
        )
        try:
            final_status = self.status()
        except Exception:
            LOGGER.exception("Loudness terminal status unavailable; preserving the mutation receipt")
            final_status = prior_status
            interrupted = True
        result = {
            "cancelled": token.is_cancelled,
            "changedCount": writer.changed_count,
            "unchangedCount": unchanged,
            "backupCount": len(writer.backups),
            "failureCount": failure_count,
            "warning": (
                "El proceso no terminó correctamente. Puede haber cambios parciales en los archivos. "
                "Conserva las copias de seguridad y revisa los archivos antes de continuar."
            )
            if interrupted or writer.failed_count
            else None,
            "status": final_status,
        }
        self.receipts = {preview.id: result}
        return result

    def shutdown(self) -> None:
        if self.engine is not None and (shutdown := getattr(self.engine.analyzer, "shutdown", None)):
            shutdown()
