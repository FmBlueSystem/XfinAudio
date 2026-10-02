"""Qt-neutral, read-only orchestration of the three original profile analyzers."""

from __future__ import annotations

import importlib
import logging
import os
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, Any

from xfinaudio.audio.analyzer import LibrosaDanceabilityAnalyzer, LibrosaEdgeSpectralAnalyzer, LibrosaSpectralAnalyzer
from xfinaudio.audio.danceability import CURRENT_DANCEABILITY_VERSION
from xfinaudio.audio.spectral_profile import CURRENT_ANALYSIS_VERSION, CURRENT_EDGE_ANALYSIS_VERSION
from xfinaudio.headless.common import BackendError, _inside
from xfinaudio.headless.serato_safety import source_identity
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.scan_service import ScanCancellationToken
from xfinaudio.library.track_repository import TrackRepository

if TYPE_CHECKING:
    from xfinaudio.headless.backend import HeadlessBackend

LOGGER = logging.getLogger(__name__)
PROFILE_FIELDS = {
    "profiles.status": set(),
    "profiles.complete": set(),
    "profiles.settings.get": set(),
    "profiles.settings.update": {"revision", "spectralCohesion"},
}
STAGES = (
    ("spectral", "spectral_profile", CURRENT_ANALYSIS_VERSION, LibrosaSpectralAnalyzer),
    ("danceability", "danceability_profile", CURRENT_DANCEABILITY_VERSION, LibrosaDanceabilityAnalyzer),
    ("edge", "edge_spectral_profile", CURRENT_EDGE_ANALYSIS_VERSION, LibrosaEdgeSpectralAnalyzer),
)


def dependencies_available() -> bool:
    """Probe lazy librosa modules only when requested work actually needs them."""
    try:
        for module in ("librosa.core.audio", "librosa.feature.spectral", "librosa.onset", "librosa.decompose"):
            importlib.import_module(module)
        return True
    except Exception:
        LOGGER.exception("Original profile dependencies are unavailable")
        return False


def _identity(path: Path, roots: list[Path]) -> tuple[object, ...] | None:
    try:
        if any(_inside(path, root) for root in roots):
            return source_identity(path)
    except (OSError, RuntimeError):
        pass
    return None


def current_records(repository: TrackRepository, records: list[TrackRecord], roots: list[Path]) -> list[TrackRecord]:
    """Reject stale versions/identities for both display counts and domain consumers."""
    paths = [record.path for record in records]
    caches = {field: getattr(repository, f"load_{field}_cache")(paths) for _, field, _, _ in STAGES}
    result = []
    for record in records:
        identity = _identity(Path(record.path), roots)
        updates = {}
        for _, field, version, _ in STAGES:
            entry = caches[field].get(record.path)
            # Original cache contract: mtime_ns, size_bytes, profile. Identity's
            # lineage and regular-file checks additionally reject path escapes.
            valid = identity is not None and entry is not None and (entry[0], entry[1]) == (identity[4], identity[3])
            updates[field] = entry[2] if valid and entry is not None and entry[2].analysis_version == version else None
        result.append(record.model_copy(update=updates))
    return result


class ProfileCompletion:
    """The server owns the single job; only at most two files are in flight."""

    def __init__(self, backend: HeadlessBackend) -> None:
        self.backend = backend
        self.failed: set[str] = set()
        self.state = "idle"
        self.max_workers = max(1, min(2, (os.cpu_count() or 2) - 1))
        self._commit_lock = threading.RLock()

    def invalidate(self) -> None:
        self.failed.clear()
        self.state = "idle"

    def status(self) -> dict[str, Any]:
        records = self.backend._records()
        counts = [sum(getattr(record, field) is not None for record in records) for _, field, _, _ in STAGES]
        ready = sum(all(getattr(record, field) is not None for _, field, _, _ in STAGES) for record in records)
        state = "idle" if not records else "complete" if ready == len(records) else self.state
        return {
            "state": state,
            "totalTracks": len(records),
            "readyCount": ready,
            "spectralReadyCount": counts[0],
            "danceabilityReadyCount": counts[1],
            "edgeReadyCount": counts[2],
            "pendingCount": len(records) - ready,
            "failedCount": len(self.failed & {record.path for record in records}),
        }

    def execute(
        self, method: str, params: dict[str, Any], token: ScanCancellationToken, emit: Callable[[dict[str, Any]], None]
    ) -> dict[str, Any]:
        if set(params) != PROFILE_FIELDS[method]:
            raise BackendError("invalid_params", "Missing or unexpected profile fields")
        if method == "profiles.settings.get":
            return self.backend.preferences.get_profiles()
        if method == "profiles.settings.update":
            result = self.backend.preferences.update_profiles(params)
            self._invalidate_contexts(scoring_only=True)
            return result
        if method == "profiles.status":
            return self.status()
        self._invalidate_contexts()
        self.invalidate()
        status = self.status()
        if token.is_cancelled:
            self.state = "cancelled"
        elif status["pendingCount"] and not dependencies_available():
            self.state = "unavailable"
        elif status["pendingCount"]:
            self._complete(token, emit)
            self.state = "cancelled" if token.is_cancelled else "partial"
        return {**self.backend._library(), "cancelled": token.is_cancelled, "status": self.status()}

    def _invalidate_contexts(self, *, scoring_only: bool = False) -> None:
        self.backend.invalidate_review()
        self.backend.live.invalidate()
        if not scoring_only:
            self.backend.editor.invalidate()
            self.backend.loudness.invalidate()
        self.backend.invalidate_optional_ai()

    def _drain_commits(self) -> None:
        with self._commit_lock:
            pass

    def _complete(self, token: ScanCancellationToken, emit: Callable[[dict[str, Any]], None]) -> None:
        subscribe = getattr(token, "subscribe", None)
        retire = subscribe(self._drain_commits) if callable(subscribe) else lambda: None
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="xfinaudio-profile") as pool:
                for stage, field, version, adapter in STAGES:
                    if token.is_cancelled:
                        break
                    paths = [Path(record.path) for record in self.backend._records() if getattr(record, field) is None]
                    done = ready = failed = 0
                    total = len(paths)

                    def progress(done: int, ready: int, failed: int, *, stage=stage, total=total) -> None:
                        emit(
                            {
                                "phase": "profiles",
                                "stage": stage,
                                "processedCount": done,
                                "totalCount": total,
                                "readyCount": ready,
                                "failedCount": failed,
                            }
                        )

                    progress(done, ready, failed)
                    analyzer = adapter()
                    # Bounded batches avoid submitting an entire large library;
                    # a cancelled job drains only the current at-most-two calls.
                    for offset in range(0, len(paths), self.max_workers):
                        if token.is_cancelled:
                            break
                        futures = [
                            pool.submit(self._analyze, analyzer, path)
                            for path in paths[offset : offset + self.max_workers]
                        ]
                        for future in futures:
                            path, identity, profile = future.result()
                            with self._commit_lock:
                                if token.is_cancelled:
                                    break
                                success = self._persist(path, identity, profile, field, version)
                            done += 1
                            ready += int(success)
                            failed += int(not success)
                            if not success:
                                self.failed.add(str(path))
                            progress(done, ready, failed)
        finally:
            retire()

    def _analyze(self, analyzer: Any, path: Path) -> tuple[Path, tuple[object, ...] | None, Any]:
        identity = _identity(path, self.backend.roots)
        profile = None
        if identity is not None:
            try:
                profile = analyzer.analyze(path)
            except Exception:
                LOGGER.exception("Original profile analysis failed")
        return path, identity, profile

    def _persist(self, path: Path, identity: tuple[object, ...] | None, profile: Any, field: str, version: int) -> bool:
        if (
            identity is None
            or profile is None
            or profile.analysis_version != version
            or _identity(path, self.backend.roots) != identity
        ):
            return False
        try:
            saved = getattr(self.backend.repository, f"update_{field}")(
                str(path), profile, expected_file_identity=(identity[4], identity[3])
            )
            return bool(saved) and _identity(path, self.backend.roots) == identity
        except Exception:
            LOGGER.exception("Profile persistence failed")
            return False
