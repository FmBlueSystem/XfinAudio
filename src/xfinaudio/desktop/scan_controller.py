"""Qt controller that owns the metadata scan thread/worker lifecycle."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Slot

from xfinaudio.application.playlist_workflow import PlaylistWorkflowService
from xfinaudio.desktop._workers import ScanWorker
from xfinaudio.library.scan_service import ScanCancellationToken


class ScanController(QObject):
    """Manage the QThread/ScanWorker lifecycle and re-emit worker signals."""

    scan_progress_updated = Signal(object)  # ScanProgress
    scan_completed = Signal(object)  # ScanResult (includes cancelled case)
    scan_failed = Signal(object)  # Exception | str
    worker_cleared = Signal()  # thread teardown done

    def __init__(self, workflow_service: PlaylistWorkflowService, *, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.workflow_service = workflow_service
        self._scan_thread: QThread | None = None
        self._scan_worker: ScanWorker | None = None
        self._current_token: ScanCancellationToken | None = None
        self._current_request_id: int = 0

    def start_scan(self, folder: Path, token: ScanCancellationToken) -> None:
        """Start a background metadata scan for *folder* using the given *token*."""
        if self._scan_thread is not None and self._scan_thread.isRunning():
            self.cancel()
            self._scan_thread.wait(500)
        self._current_token = token
        self._current_request_id += 1
        rid = self._current_request_id
        self._start_scan_worker(folder, token, rid)

    def cancel(self) -> None:
        """Request cancellation if a scan is running.

        Flips the cooperative ScanCancellationToken (which the worker loop in
        scan_service checks via ``is_cancelled``) AND requests thread
        interruption. The token flip is what actually stops the scan loop;
        requestInterruption alone is not observed by the worker.
        """
        if self._current_token is not None:
            self._current_token.cancel()
        if self._scan_thread is not None and self._scan_thread.isRunning():
            self._scan_thread.requestInterruption()
            self._scan_thread.wait(500)

    def _start_scan_worker(self, folder: Path, token: ScanCancellationToken, request_id: int) -> None:
        """Construct and start the QThread/ScanWorker pair."""
        thread = QThread(self)
        worker = ScanWorker(
            lambda progress_callback: self.workflow_service.scan_folder(
                folder,
                on_progress=progress_callback,
                cancellation_token=token,
            ),
            request_id=request_id,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_worker_progress)
        worker.finished.connect(lambda result, rid=request_id: self._on_worker_finished(result, rid))
        worker.failed.connect(lambda error, rid=request_id: self._on_worker_failed(error, rid))
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

    def _on_worker_finished(self, result: object, request_id: int | None = None) -> None:
        if request_id is not None and request_id != self._current_request_id:
            return  # stale result — discard
        self.scan_completed.emit(result)

    def _on_worker_failed(self, error: object, request_id: int | None = None) -> None:
        if request_id is not None and request_id != self._current_request_id:
            return  # stale error — discard
        self.scan_failed.emit(error)

    def _on_worker_cleared(self) -> None:
        sender_thread = self.sender()
        if sender_thread is not None and sender_thread is not self._scan_thread:
            return  # stale cleanup — don't clobber a newer thread
        self._scan_thread = None
        self._scan_worker = None
        self.worker_cleared.emit()
