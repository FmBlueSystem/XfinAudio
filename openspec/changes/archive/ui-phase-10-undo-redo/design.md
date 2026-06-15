# Design: Undo/Redo

## Decision question

How do we add undo/redo without breaking existing functionality?

## Alternatives considered

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. Command pattern with stack | Flexible; extensible | More boilerplate | **Selected** |
| B. State snapshots | Simple | Memory intensive | Rejected |
| C. Event sourcing | Auditable | Over-engineered | Rejected |

## Architecture impact

- `undo_manager.py` (new): UndoManager with command stack
- `main_window.py`: Integrate undo/redo shortcuts and buttons
- `library_screen.py`: Track removal uses undo manager

## Affected files

- `src/xfinaudio/desktop/undo_manager.py` (new)
- `src/xfinaudio/desktop/main_window.py`
- `src/xfinaudio/desktop/screens/library_screen.py`
- `tests/test_undo_manager.py` (new)
- `tests/test_main_window.py`
