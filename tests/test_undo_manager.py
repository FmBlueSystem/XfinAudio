from __future__ import annotations

from xfinaudio.desktop.undo_manager import Command, UndoManager


def test_undo_manager_lifo_redo_history_and_redo_clear() -> None:
    manager = UndoManager()
    log: list[str] = []

    def command(label: str) -> Command:
        return Command(label, lambda: log.append(f"execute:{label}"), lambda: log.append(f"undo:{label}"))

    manager.undo()
    manager.redo()
    manager.push(command("a"))
    manager.push(command("b"))
    assert manager.history() == ["b", "a"]

    manager.undo()
    manager.undo()
    assert log == ["undo:b", "undo:a"]
    assert manager.can_redo is True

    manager.redo()
    manager.redo()
    assert log == ["undo:b", "undo:a", "execute:a", "execute:b"]

    manager.undo()
    manager.push(command("c"))
    assert manager.can_redo is False
    assert manager.history() == ["c", "a"]
