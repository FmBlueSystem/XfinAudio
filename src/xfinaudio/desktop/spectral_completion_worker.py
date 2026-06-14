"""Background worker that completes spectral profiles after a metadata scan.

The metadata scan returns tracks immediately (BPM, key, energy, status) while
this worker computes spectral colors progressively in a background thread and
emits each result back to the UI.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal, Slot

from xfinaudio.audio.spectral_profile import SpectralProfile, analyze_spectral_profile
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.scan_service import ScanCancellationToken

LOGGER = logging.getLogger(__name__)


def _is_cancelled(token: ScanCancellationToken | None) -> bool:
    """Return True if cancellation has been requested."""
    if token is not None and token.is_cancelled:
        return True
    thread = QThread.currentThread()
    return thread is not None and thread.isInterruptionRequested()


class _SpectralCompletionRunner(QObject):
    """Internal runner that lives on a background QThread."""

    progress = Signal(str, object)  # path, SpectralProfile | None
    finished = Signal()
    failed = Signal(object)

    def __init__(
        self,
        records: Sequence[TrackRecord],
        repository: Any,
        cancellation_token: ScanCancellationToken | None = None,
        max_workers: int | None = None,
    ) -> None:
        super().__init__()
        self._records = records
        self._repository = repository
        self._cancellation_token = cancellation_token
        self._max_workers = max_workers or min(os.cpu_count() or 4, 8)

    @Slot()
    def run(self) -> None:
        try:
            self._run_completion()
        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.exception("Spectral completion runner failed")
            self.failed.emit(exc)
        finally:
            self.finished.emit()

    def _run_completion(self) -> None:
        paths = [record.path for record in self._records if record.spectral_profile is None]
        if not paths or _is_cancelled(self._cancellation_token):
            return

        # Reuse any persistent cache entries first.
        cached_profiles: dict[str, SpectralProfile] = {}
        if hasattr(self._repository, "load_spectral_profile_cache"):
            cache = self._repository.load_spectral_profile_cache(paths)
            for path in paths:
                entry = cache.get(path)
                if entry is not None:
                    cached_profiles[path] = entry[2]
                    self.progress.emit(path, entry[2])

        pending_paths = [Path(path) for path in paths if path not in cached_profiles]
        if not pending_paths:
            return

        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            future_to_path: dict[Any, Path] = {
                pool.submit(analyze_spectral_profile, path): path for path in pending_paths
            }
            for future in as_completed(future_to_path):
                if _is_cancelled(self._cancellation_token):
                    for pending in future_to_path:
                        pending.cancel(False)
                    break
                path = future_to_path[future]
                try:
                    profile = future.result()
                except Exception:
                    LOGGER.exception("Spectral analysis failed for %s", path)
                    profile = None
                if _is_cancelled(self._cancellation_token):
                    break
                if profile is not None and hasattr(self._repository, "update_spectral_profile"):
                    try:
                        self._repository.update_spectral_profile(str(path), profile)
                    except Exception:
                        LOGGER.exception("Failed to persist spectral profile for %s", path)
                self.progress.emit(str(path), profile)


class SpectralCompletionWorker(QObject):
    """Public controller for lazy spectral profile completion.

    Usage:
        worker = SpectralCompletionWorker()
        worker.progress.connect(handle_profile)
        worker.finished.connect(handle_done)
        worker.start(records, repository)
    """

    progress = Signal(str, object)  # path, SpectralProfile | None
    finished = Signal()
    failed = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread: QThread | None = None
        self._runner: _SpectralCompletionRunner | None = None
        self._cancellation_token: ScanCancellationToken | None = None

    def start(
        self,
        records: Sequence[TrackRecord],
        repository: Any,
        cancellation_token: ScanCancellationToken | None = None,
        max_workers: int | None = None,
    ) -> None:
        """Start completing missing spectral profiles in a background thread."""
        self.cancel()
        self._cancellation_token = cancellation_token
        thread = QThread(self)
        runner = _SpectralCompletionRunner(records, repository, cancellation_token, max_workers)
        runner.moveToThread(thread)
        thread.started.connect(runner.run)
        runner.progress.connect(self.progress)
        runner.finished.connect(self._on_finished)
        runner.failed.connect(self.failed)
        runner.finished.connect(thread.quit)
        runner.finished.connect(runner.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._thread = thread
        self._runner = runner
        thread.start()

    def cancel(self, timeout_ms: int = 500) -> None:
        """Request cancellation and wait for the background thread to finish."""
        if self._cancellation_token is not None:
            self._cancellation_token.cancel()
        if self._thread is not None and self._thread.isRunning():
            self._thread.requestInterruption()
            self._thread.wait(timeout_ms)

    def wait(self, timeout_ms: int = 5000) -> bool:
        """Wait for the background thread to finish.

        Returns True if the thread finished within the timeout.
        """
        if self._thread is None:
            return True
        return self._thread.wait(timeout_ms)

    @Slot()
    def _on_finished(self) -> None:
        self.finished.emit()
        self._runner = None
