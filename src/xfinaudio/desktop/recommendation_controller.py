"""Qt controller that owns the recommendation thread/worker lifecycle."""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal

from xfinaudio.application.playlist_workflow import PlaylistWorkflowService
from xfinaudio.desktop._workers import BackgroundWorker
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls


class RecommendationController(QObject):
    """Manage the QThread/BackgroundWorker lifecycle and re-emit worker signals."""

    recommendation_completed = Signal(object)  # workflow result
    recommendation_failed = Signal(object)  # Exception | str
    worker_cleared = Signal()  # thread teardown done

    def __init__(self, workflow_service: PlaylistWorkflowService, *, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.workflow_service = workflow_service
        self._recommendation_thread: QThread | None = None
        self._recommendation_worker: BackgroundWorker | None = None
        self._current_request_id: int = 0

    def start_recommendation(
        self,
        records: list[TrackRecord],
        strategy_name: str,
        controls: DJControls | None = None,
    ) -> None:
        """Start a background recommendation in a worker thread."""
        if self._recommendation_thread is not None and self._recommendation_thread.isRunning():
            self.cancel()
            self._recommendation_thread.wait(500)
        self._current_request_id += 1
        rid = self._current_request_id
        self._start_recommendation_worker(records, strategy_name, controls, rid)

    def cancel(self) -> None:
        """Request thread interruption if a recommendation is running."""
        if self._recommendation_thread is not None and self._recommendation_thread.isRunning():
            # No cooperative token — worker runs to completion; stale results
            # discarded via request_id.
            self._recommendation_thread.requestInterruption()
            self._recommendation_thread.wait(500)

    def _start_recommendation_worker(
        self,
        records: list[TrackRecord],
        strategy_name: str,
        controls: DJControls | None,
        request_id: int,
    ) -> None:
        """Construct and start the QThread/BackgroundWorker pair."""
        thread = QThread(self)
        worker = BackgroundWorker(
            lambda: self.workflow_service.recommend(records, strategy_name, controls=controls),
            request_id=request_id,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(lambda result, rid=request_id: self._on_worker_finished(result, rid))
        worker.failed.connect(lambda error, rid=request_id: self._on_worker_failed(error, rid))
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_worker_cleared)
        self._recommendation_thread = thread
        self._recommendation_worker = worker
        thread.start()

    def _on_worker_finished(self, result: object, request_id: int | None = None) -> None:
        if request_id is not None and request_id != self._current_request_id:
            return  # stale result — discard
        self.recommendation_completed.emit(result)

    def _on_worker_failed(self, error: object, request_id: int | None = None) -> None:
        if request_id is not None and request_id != self._current_request_id:
            return  # stale error — discard
        self.recommendation_failed.emit(error)

    def _on_worker_cleared(self) -> None:
        sender_thread = self.sender()
        if sender_thread is not None and sender_thread is not self._recommendation_thread:
            return  # stale cleanup — don't clobber a newer thread
        self._recommendation_thread = None
        self._recommendation_worker = None
        self.worker_cleared.emit()
