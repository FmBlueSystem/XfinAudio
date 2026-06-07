"""Qt controller that owns the recommendation thread/worker lifecycle."""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal, Slot

from xfinaudio.desktop._workers import BackgroundWorker
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls


class RecommendationController(QObject):
    """Manage the QThread/BackgroundWorker lifecycle and re-emit worker signals."""

    recommendation_completed = Signal(object)  # workflow result
    recommendation_failed = Signal(object)  # Exception | str
    worker_cleared = Signal()  # thread teardown done

    def __init__(self, workflow_service: object, *, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.workflow_service = workflow_service
        self._recommendation_thread: QThread | None = None
        self._recommendation_worker: BackgroundWorker | None = None

    def start_recommendation(
        self,
        records: list[TrackRecord],
        strategy_name: str,
        controls: DJControls | None = None,
    ) -> None:
        """Start a background recommendation in a worker thread."""
        thread = QThread(self)
        worker = BackgroundWorker(lambda: self.workflow_service.recommend(records, strategy_name, controls=controls))
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_worker_finished)
        worker.failed.connect(self._on_worker_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_worker_cleared)
        self._recommendation_thread = thread
        self._recommendation_worker = worker
        thread.start()

    @Slot(object)
    def _on_worker_finished(self, result: object) -> None:
        self.recommendation_completed.emit(result)

    @Slot(object)
    def _on_worker_failed(self, error: object) -> None:
        self.recommendation_failed.emit(error)

    @Slot()
    def _on_worker_cleared(self) -> None:
        self._recommendation_thread = None
        self._recommendation_worker = None
        self.worker_cleared.emit()
