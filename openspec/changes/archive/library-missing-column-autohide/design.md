# Design: Auto-hide Missing Column in Library Screen

## Decision question

How can we give the DJ more horizontal space without losing the Missing metadata column entirely?

## Alternatives considered (Arbor-style)

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. Toggle button in top controls | Discoverable; explicit user control; easy to test. | Adds one more button to the top row. | **Selected.** |
| B. Right-click context menu on table | No extra UI chrome. | Harder to discover; more code for a single action. | Rejected. |
| C. Collapsible section replacing the column | Gains a lot of space. | Breaks the table metaphor; complex layout changes. | Rejected. |
| D. Persist state in AppSettings | Survives restart. | Adds settings migration/UI clutter for a minor preference. | Rejected for this slice. |

## Architecture impact

`LibraryScreen` owns the visible track table. The implementation adds:

- A `_MISSING_COLUMN` constant (index 7).
- A `QPushButton` toggle in the top controls row.
- A `_missing_column_visible` boolean.
- A `_toggle_missing_column()` slot that calls `tracks_table.setColumnHidden(_MISSING_COLUMN, not visible)` and updates button text.
- Initial column hidden state set during `_build_ui()`.

The table continues to use the Path column (last column, hidden by default) as the stable lookup key, so hiding Missing does not affect row selection, filtering, or sorting.

## Affected files

- `src/xfinaudio/desktop/screens/library_screen.py`
- `tests/test_library_screen.py`

## Safety

- No audio mutation.
- No DSP scope expansion.
- No live Serato Database V2 writes.
