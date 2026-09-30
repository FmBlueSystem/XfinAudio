"""Qt worker objects that run XfinAudio workflow operations off the UI thread."""

from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import QObject, QThread, Signal, Slot

from xfinaudio.library.scan_service import ScanProgress

LOGGER = logging.getLogger(__name__)


class WorkerRegistry(QObject):
    """Retain every request, including superseded workers, until its thread exits."""

    def __init__(self, parent: QObject) -> None:
        super().__init__(parent)
        self._workers: dict[QThread, QObject] = {}

    def retain(self, thread: QThread, worker: QObject) -> None:
        self._workers[thread] = worker
        # Keep Python wrappers alive through Qt's deferred worker deletion, not
        # merely until finished is queued while the worker thread still unwinds.
        thread.destroyed.connect(lambda: self._workers.pop(thread, None))


class BackgroundWorker(QObject):
    """Run one workflow operation away from the Qt UI thread."""

    finished = Signal(object)
    failed = Signal(object)

    def __init__(self, operation: Callable[[], object], request_id: int = 0) -> None:
        super().__init__()
        self._operation = operation
        self._request_id = request_id

    @Slot()
    def run(self) -> None:
        """Execute the operation and publish its result back to the UI thread."""
        try:
            result = self._operation()
        except Exception as exc:  # pragma: no cover - exercised through Qt signal plumbing
            LOGGER.exception("Background worker operation failed")
            self.failed.emit(exc)
            return
        self.finished.emit(result)


class ScanWorker(QObject):
    """Run metadata scanning away from the Qt UI thread."""

    progress = Signal(object)
    finished = Signal(object)
    failed = Signal(object)

    def __init__(self, operation: Callable[[Callable[[ScanProgress], None]], object], request_id: int = 0) -> None:
        super().__init__()
        self._operation = operation
        self._request_id = request_id

    @Slot()
    def run(self) -> None:
        """Execute the scan operation and publish progress/results through Qt signals."""
        try:
            result = self._operation(self.progress.emit)
        except Exception as exc:  # pragma: no cover - exercised through Qt signal plumbing
            LOGGER.exception("Scan worker operation failed")
            self.failed.emit(exc)
            return
        self.finished.emit(result)


__all__ = ["BackgroundWorker", "ScanWorker"]
