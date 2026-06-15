# Design: Contextual Tooltips

## Decision question

How do we add tooltips without cluttering the codebase?

## Alternatives considered

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. Add setToolTip() calls | Simple; inline | Scattered across files | **Selected** |
| B. Centralized tooltip config | Centralized | More complex | Rejected |
| C. Tooltip database | Flexible | Over-engineered | Rejected |

## Architecture impact

- `library_screen.py`, `build_screen.py`, `export_screen.py`, `review_screen.py`: Add setToolTip() calls

## Affected files

- `src/xfinaudio/desktop/screens/library_screen.py`
- `src/xfinaudio/desktop/screens/build_screen.py`
- `src/xfinaudio/desktop/screens/export_screen.py`
- `src/xfinaudio/desktop/screens/review_screen.py`
- `tests/test_library_screen.py`, `tests/test_build_screen.py`, `tests/test_export_screen.py`, `tests/test_review_screen.py`
