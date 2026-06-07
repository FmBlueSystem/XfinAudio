"""Qt controller that owns the metadata scan thread/worker lifecycle."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Slot

from xfinaudio.desktop._workers import ScanWorker
from xfinaudio.library.scan_service import ScanCancellationToken


class ScanController(QObject):
    """Manage the QThread/ScanWorker lifecycle and re-emit worker signals."""

    scan_progress_updated = Signal(object)  # ScanProgress
    scan_completed = Signal(object)  # ScanResult (includes cancelled case)
    scan_failed = Signal(object)  # Exception | str
    worker_cleared = Signal()  # thread teardown done

    def __init__(self, workflow_service: object, *, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.workflow_service = workflow_service
        self._scan_thread: QThread | None = None
        self._scan_worker: ScanWorker | None = None

    def start_scan(self, folder: Path, token: ScanCancellationToken) -> None:
        """Start a background metadata scan for *folder* using the given *token*."""
        self._start_scan_worker(folder, token)

    def cancel(self, token: ScanCancellationToken | None) -> None:
        """Request cooperative cancellation if a token is active."""
        if token is not None:
            token.cancel()

    def _start_scan_worker(self, folder: Path, token: ScanCancellationToken) -> None:
        """Construct and start the QThread/ScanWorker pair."""
        thread = QThread(self)
        worker = ScanWorker(
            lambda progress_callback: self.workflow_service.scan_folder(
                folder,
                on_progress=progress_callback,
                cancellation_token=token,
            )
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_worker_progress)
        worker.finished.connect(self._on_worker_finished)
        worker.failed.connect(self._on_worker_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_worker_cleared)
        self._scan_thread = thread
        self._scan_worker = worker
        thread.start()

    @Slot(object)
    def _on_worker_progress(self, progress: object) -> None:
        self.scan_progress_updated.emit(progress)

    @Slot(object)
    def _on_worker_finished(self, result: object) -> None:
        self.scan_completed.emit(result)

    @Slot(object)
    def _on_worker_failed(self, error: object) -> None:
        self.scan_failed.emit(error)

    @Slot()
    def _on_worker_cleared(self) -> None:
        self._scan_thread = None
        self._scan_worker = None
        self.worker_cleared.emit()
