# Design: Space Utilization

## Decision question

How do we make the track table use available vertical space?

## Alternatives considered

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. Remove max height + set Expanding | Simple; uses Qt layout system | May break tests checking exact heights | **Selected** |
| B. Calculate height from window size | Precise control | Complex; breaks on resize | Rejected |
| C. Use QSplitter | User-resizable | Over-engineered for this phase | Rejected |

## Architecture impact

- `main_window.py`: Change `setMinimumHeight(132)` to `setMinimumHeight(400)` and remove `setMaximumHeight(190)`
- `main_window.py`: Add `setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)`
- `theme.py`: Remove `_COMPACT_LIBRARY_TABLE_MAX_HEIGHT` and `_COMPACT_LIBRARY_TABLE_MIN_HEIGHT` constants

## Affected files

- `src/xfinaudio/desktop/main_window.py`
- `src/xfinaudio/desktop/theme.py`
- `tests/test_main_window.py` (if any tests check these values)
