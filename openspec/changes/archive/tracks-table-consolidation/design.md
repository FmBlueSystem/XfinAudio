# Design: Consolidate Tracks Table Ownership

## Decision question

How do we remove the dead `MainWindow.tracks_table` without regressing behavior?

## Alternatives considered (Arbor-style)

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. Migrate all references to `self._library_screen.tracks_table` | Simple; minimal risk. | Touches many call sites in main_window. | **Selected.** |
| B. Make MainWindow a thin wrapper that delegates every table call to LibraryScreen | Cleanest separation. | Adds boilerplate. | Rejected for this slice. |
| C. Keep dual tables but route all writes to both | Defensive. | Doubles maintenance; the dead table stays. | Rejected. |

## Architecture impact

`LibraryScreen` becomes the sole owner of the library track table. `MainWindow` keeps its filter, sort, and populate logic but delegates to the screen.

## Affected files

- `src/xfinaudio/desktop/main_window.py`
- `tests/test_main_window.py`
- `tests/test_library_screen.py`

## Safety

- No audio mutation.
- No DSP scope expansion.
- No live Serato Database V2 writes.
