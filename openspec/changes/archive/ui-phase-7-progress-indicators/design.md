# Design: Progress Indicators

## Decision question

How do we add progress feedback without cluttering the UI?

## Alternatives considered

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. Progress bars in buttons | Integrated; clear | Takes button space | **Selected** |
| B. Modal dialog | Focused | Blocks UI | Rejected |
| C. Status bar message | Minimal | Not visible enough | Rejected |

## Architecture impact

- `library_screen.py`: Add QProgressBar to scan button area
- `build_screen.py`: Add QProgressBar to recommend button area
- `export_screen.py`: Add QProgressBar to export button area
- `scan_controller.py`: Track progress and emit signals

## Affected files

- `src/xfinaudio/desktop/screens/library_screen.py`
- `src/xfinaudio/desktop/screens/build_screen.py`
- `src/xfinaudio/desktop/screens/export_screen.py`
- `src/xfinaudio/desktop/scan_controller.py`
- `tests/test_library_screen.py`, `tests/test_build_screen.py`, `tests/test_export_screen.py`
