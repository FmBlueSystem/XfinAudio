# Design: Quick Filter Bar

## Decision question

How do we add quick filters without cluttering the UI?

## Alternatives considered

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. Filter bar above table | Always visible; easy to use | Takes vertical space | **Selected** |
| B. Dropdown menu | Compact | Hidden by default; harder to discover | Rejected |
| C. Sidebar filters | Persistent; clear | Takes horizontal space | Rejected |

## Architecture impact

- `library_screen.py`: Add filter bar layout above the table
- `library_view_model.py`: Add filter state management
- `theme.py`: Add filter chip styles

## Affected files

- `src/xfinaudio/desktop/screens/library_screen.py`
- `src/xfinaudio/desktop/library_view_model.py`
- `src/xfinaudio/desktop/theme.py`
- `tests/test_library_screen.py`
