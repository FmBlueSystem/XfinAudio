from __future__ import annotations

from xfinaudio.desktop.undo_manager import UNDO_HISTORY_LIMIT, Command, UndoManager


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


def test_undo_stack_is_bounded_and_drops_oldest_commands() -> None:
    """Each command closes over a full PlaylistRecommendation, so the stack must be capped."""
    manager = UndoManager()

    for index in range(UNDO_HISTORY_LIMIT + 10):
        manager.push(Command(label=f"cmd{index}", execute=lambda: None, undo=lambda: None))

    history = manager.history()
    assert len(history) == UNDO_HISTORY_LIMIT
    assert history[0] == f"cmd{UNDO_HISTORY_LIMIT + 9}"
    assert history[-1] == "cmd10"
