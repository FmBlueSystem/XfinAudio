"""Keep bounded AI probes responsive and ignore cancelled/stale results."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QThread, Signal, Slot

from xfinaudio.ai.connection_test import ConnectionStatus, run_connection_test
from xfinaudio.config.settings import AiSettings

Operation = Callable[[AiSettings], ConnectionStatus]
# Dialogs may close while a request finishes. A running thread must never be
# parented to the dialog or released before Qt completes its deferred deletion.
_ACTIVE: set[_ProbeThread] = set()


class _ProbeThread(QThread):
    result = Signal(int, object)

    def __init__(self, generation: int, operation: Operation, settings: AiSettings) -> None:
        super().__init__()
        self._generation, self._operation, self._settings = generation, operation, settings
        _ACTIVE.add(self)
        self.destroyed.connect(lambda: _ACTIVE.discard(self))
        self.finished.connect(self.deleteLater)

    def run(self) -> None:
        try:
            result = self._operation(self._settings)
        except Exception:
            result = ConnectionStatus("unavailable", "Connection unavailable. Check configuration and retry.")
        self.result.emit(self._generation, result)


class ConnectionProbe(QObject):
    """One active request per owner; cancel invalidates results, not sent data."""

    completed = Signal(object)
    busy_changed = Signal(bool)

    def __init__(self, parent: QObject | None = None, *, operation: Operation = run_connection_test) -> None:
        super().__init__(parent)
        self._operation = operation
        self._task: _ProbeThread | None = None
        self._generation = 0

    @property
    def busy(self) -> bool:
        return self._task is not None

    def start(self, settings: AiSettings) -> bool:
        if self.busy:
            return False
        self._generation += 1
        self._task = _ProbeThread(self._generation, self._operation, settings)
        self._task.result.connect(self._complete)
        self._task.finished.connect(self._finished)
        self.busy_changed.emit(True)
        self._task.start()
        return True

    def cancel(self) -> None:
        self._generation += 1

    @Slot(int, object)
    def _complete(self, generation: int, status: ConnectionStatus) -> None:
        if generation == self._generation:
            self.completed.emit(status)

    @Slot()
    def _finished(self) -> None:
        self._task = None
        self.busy_changed.emit(False)
