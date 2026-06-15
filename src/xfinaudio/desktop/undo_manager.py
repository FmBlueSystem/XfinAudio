from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    label: str
    execute: Callable[[], None]
    undo: Callable[[], None]


class UndoManager:
    def __init__(self) -> None:
        self._undo_stack: list[Command] = []
        self._redo_stack: list[Command] = []

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    def push(self, command: Command) -> None:
        self._undo_stack.append(command)
        self._redo_stack.clear()

    def undo(self) -> None:
        if self._undo_stack:
            command = self._undo_stack.pop()
            command.undo()
            self._redo_stack.append(command)

    def redo(self) -> None:
        if self._redo_stack:
            command = self._redo_stack.pop()
            command.execute()
            self._undo_stack.append(command)

    def history(self) -> list[str]:
        return [command.label for command in reversed(self._undo_stack)]
