"""Retained asynchronous Prep generation with GUI-thread result publication."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QThread, Signal, Slot

from xfinaudio.desktop._workers import BackgroundWorker, WorkerRegistry
from xfinaudio.desktop.app_state import AppState
from xfinaudio.recommendation.prep_copilot import PrepCopilotPlan


class PrepGenerationTask(QObject):
    completed = Signal(object, int)
    failed = Signal(object, int)

    def __init__(
        self,
        parent: QObject,
        *,
        state_getter: Callable[[], AppState],
        state_setter: Callable[[AppState], None],
        on_state_changed: Callable[[], None],
        on_completed: Callable[[PrepCopilotPlan], None],
        on_status: Callable[[str], None],
    ) -> None:
        super().__init__(parent)
        self._get = state_getter
        self._set = state_setter
        self._changed = on_state_changed
        self._publish = on_completed
        self._status = on_status
        self._registry = WorkerRegistry(self)
        self._request_id = 0
        self._thread: QThread | None = None
        self.completed.connect(self._on_completed)
        self.failed.connect(self._on_failed)

    def start(self, operation: Callable[[], PrepCopilotPlan]) -> None:
        if self._get().is_preparing_copilot:
            return
        self._request_id += 1
        request_id = self._request_id
        self._set(self._get().model_copy(update={"is_preparing_copilot": True}))
        self._changed()
        self._status(self.tr("Generating Prep Copilot variants..."))
        thread = QThread(self)
        worker = BackgroundWorker(operation, request_id=request_id)
        self._registry.retain(thread, worker)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(lambda result: self.completed.emit(result, request_id))
        worker.failed.connect(lambda error: self.failed.emit(error, request_id))
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_thread)
        self._thread = thread
        thread.start()

    def cancel(self) -> None:
        self._request_id += 1
        if self._thread is not None and self._thread.isRunning():
            self._thread.requestInterruption()
        if self._get().is_preparing_copilot:
            self._finish()
            self._status(self.tr("Prep generation cancelled; previous results kept"))

    def _finish(self) -> None:
        self._set(self._get().model_copy(update={"is_preparing_copilot": False}))
        self._changed()

    @Slot(object, int)
    def _on_completed(self, result: object, request_id: int) -> None:
        if request_id != self._request_id:
            return
        self._finish()
        if isinstance(result, PrepCopilotPlan):
            self._publish(result)

    @Slot(object, int)
    def _on_failed(self, error: object, request_id: int) -> None:
        if request_id != self._request_id:
            return
        self._finish()
        self._status(self.tr("Prep generation failed; previous results kept: {0}").format(error))

    @Slot()
    def _clear_thread(self) -> None:
        if self.sender() is self._thread:
            self._thread = None
