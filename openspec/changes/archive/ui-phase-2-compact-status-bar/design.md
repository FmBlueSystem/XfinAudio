# Design: Compact Status Bar

## Decision question

How do we reclaim vertical space from status labels without losing information?

## Alternatives considered

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. Status bar at bottom | Reclaims space; collapsible | Users may miss status info | **Selected** |
| B. Overlay status | Always visible | Obscures content | Rejected |
| C. Keep at top | Familiar | Wastes space | Rejected |

## Architecture impact

- `status_bar.py` (new): Create StatusBar widget
- `main_window.py`: Add status bar to layout
- `library_screen.py`: Remove status labels

## Affected files

- `src/xfinaudio/desktop/status_bar.py` (new)
- `src/xfinaudio/desktop/main_window.py`
- `src/xfinaudio/desktop/screens/library_screen.py`
- `tests/test_main_window.py`
