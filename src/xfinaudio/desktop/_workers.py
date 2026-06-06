"""Qt worker objects that run XfinAudio workflow operations off the UI thread."""

from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import QObject, Signal, Slot

from xfinaudio.library.scan_service import ScanProgress

LOGGER = logging.getLogger(__name__)


class BackgroundWorker(QObject):
    """Run one workflow operation away from the Qt UI thread."""

    finished = Signal(object)
    failed = Signal(object)

    def __init__(self, operation: Callable[[], object]) -> None:
        super().__init__()
        self._operation = operation

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

    def __init__(self, operation: Callable[[Callable[[ScanProgress], None]], object]) -> None:
        super().__init__()
        self._operation = operation

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
