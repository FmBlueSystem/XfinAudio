"""Small reusable QThread stage for completion work that emits typed results."""

from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot

from xfinaudio.desktop._workers import WorkerRegistry

LOGGER = logging.getLogger(__name__)
CompletionTask = Callable[[Callable[[str, object], None]], object]


class _Runner(QObject):
    result = Signal(str, object)
    finished = Signal()

    def __init__(self, task: CompletionTask) -> None:
        super().__init__()
        self._task = task

    @Slot()
    def run(self) -> None:
        try:
            self._task(self.result.emit)
        except Exception:  # pragma: no cover - defensive boundary
            LOGGER.exception("Background completion failed")
        finally:
            self.finished.emit()


class BackgroundCompletionStage(QObject):
    """Run any completion task once without adding a feature-specific Qt worker."""

    result = Signal(str, object)
    finished = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._worker_registry = WorkerRegistry(self)
        self._thread: QThread | None = None
        self._runner: _Runner | None = None
        self._cancel: Callable[[], None] | None = None

    def start(self, task: CompletionTask, *, cancel: Callable[[], None] | None = None) -> None:
        self.cancel()
        if self.is_running():
            return
        self._cancel = cancel
        thread, runner = QThread(self.parent()), _Runner(task)
        self._worker_registry.retain(thread, runner)
        runner.moveToThread(thread)
        thread.started.connect(runner.run)
        runner.result.connect(self.result)
        runner.finished.connect(thread.quit, Qt.ConnectionType.DirectConnection)
        thread.finished.connect(self._clear)
        thread.finished.connect(self.finished)
        thread.finished.connect(runner.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._thread, self._runner = thread, runner
        thread.start()

    def cancel(self, timeout_ms: int = 0) -> None:
        if self._cancel is not None:
            self._cancel()
        if self._thread is not None and self._thread.isRunning():
            self._thread.requestInterruption()
            self._thread.quit()
            if timeout_ms:
                self._thread.wait(timeout_ms)

    def shutdown(self) -> None:
        """Request cancellation; the shell keeps the event loop alive until idle."""
        self.cancel()

    def dispose_when_idle(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            self._thread.finished.connect(self.deleteLater)
        else:
            self.deleteLater()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    @Slot()
    def _clear(self) -> None:
        self._thread = self._runner = None
        self._cancel = None
