# Design: slim-main-window-qt-coordinator

## Overview

This change is a behavior-preserving refactor of the desktop `MainWindow`. The first implementation slice extracts library and recommendation table row population into a focused helper module while keeping `MainWindow` as the public Qt coordinator and preserving all existing widget attributes, wrapper methods, sorting/filtering behavior, and entry points.

The slice intentionally avoids constructor/page-builder extraction, worker changes, state-model migration, and product/UX changes so the implementation can stay within the <=400 changed-line review budget.

## Goals

- Move table rendering loops for the library and recommendation tables out of `src/xfinaudio/desktop/main_window.py`.
- Keep `MainWindow._populate_track_table(...)` and `MainWindow.show_recommendation(...)` callable as thin compatibility wrappers.
- Preserve `_SortAwareTableItem` semantics through a reusable table item seam used by the extracted helpers.
- Preserve observable table behavior: row counts, cell text, column order, row-to-record mapping, filtering, sorting, and recommendation warning formatting.
- Validate via strict TDD using offscreen Qt tests and `uv run pytest -q`.

## Non-goals

- No MVP/MVVM rewrite.
- No changes to `xfinaudio.desktop.app:main` or `MainWindow.with_defaults`.
- No widget construction/layout extraction in this first slice unless the implementation remains comfortably under budget.
- No migration of mutable `MainWindow` fields to `WindowState`.
- No extraction of DJ readiness, transition review, Prep Copilot, or Serato export history populators in this slice.
- No copy, label, header, control-state, visual, or workflow changes.

## Current behavior to preserve

### Library table

`MainWindow._populate_track_table(records)` currently:

1. Replaces `self._records_by_path` with `{record.path: record for record in records}`.
2. Sets `self.tracks_table` row count to `len(records)`.
3. Writes 10 columns in the existing order:
   - `Title`, `Artist`, `BPM`, `Key`, `Energy`, `Missing`, `Genre`, `Tags/Subgenre`, `Status`, `Path`.
4. Uses `_table_item(...)`, backed by `_SortAwareTableItem`, for all cells.
5. Formats BPM with `f"{record.bpm:g}"`, blank for missing BPM.
6. Formats energy as `str(record.energy_level)`, blank for missing energy.
7. Formats missing metadata through existing `_format_missing_metadata` behavior.
8. Formats tags through existing `_format_track_tags` behavior.
9. Calls `_apply_song_filter(clear_selection=False)` after population.

Filtering and selected-track lookup depend on the path cell and `_records_by_path`; the wrapper remains responsible for applying filters after helper population.

### Recommendation table

`MainWindow.show_recommendation(records, strategy_name, explanation)` currently:

1. Expands/collapses recommendation sections based on `bool(records)`.
2. Sets `self.recommendation_table` row count to `len(records)`.
3. Writes 11 columns in the existing order:
   - `Title`, `Artist`, `BPM`, `Key`, `Energy`, `Genre`, `Tags/Subgenre`, `Strategy`, `Path`, `Transition Score`, `Warnings`.
4. Uses transition row `row_index - 1` for recommendation rows after the first row.
5. Formats transition score as `f"{transition.final_score:.3f}"`; blank for the first row/no transition.
6. Formats warnings with existing `format_recommendation_warning(...)` and joins them with `"; "`.
7. Uses `_table_item(...)` / `_SortAwareTableItem` for stable text display and typed sorting.

The wrapper must not mutate `explanation` and must preserve current downstream state/control behavior owned by the recommendation workflow.

## Proposed structure

Add:

- `src/xfinaudio/desktop/table_populators.py`

Keep in `main_window.py` unless later reuse justifies moving them:

- `_SortAwareTableItem`
- `_table_item`
- `_format_track_tags`
- `_format_missing_metadata`
- `format_recommendation_warning`

The new module should import only the domain types and Qt table type it needs, and receive formatting/item dependencies explicitly. This keeps helpers testable and avoids circular imports from `table_populators.py` back into `main_window.py`.

## Helper contracts

### Table item seam

Define a simple callable protocol/type alias in `table_populators.py`:

```python
TableItemFactory = Callable[[str, object | None], QTableWidgetItem]
```

`MainWindow` wrappers pass the existing `_table_item` function. This preserves `_SortAwareTableItem` behavior without making the new helper module own the private class.

### `populate_library_table`

Signature:

```python
def populate_library_table(
    table: QTableWidget,
    records: Sequence[TrackRecord],
    *,
    item_factory: TableItemFactory,
    format_missing_metadata: Callable[[TrackRecord], str],
    format_track_tags: Callable[[TrackRecord], str],
) -> dict[str, TrackRecord]:
    ...
```

Responsibilities:

- Set `table.setRowCount(len(records))`.
- Populate all existing library columns with identical display text and sort values.
- Return `{record.path: record for record in records}` so the `MainWindow` wrapper can update `self._records_by_path` without the helper mutating window state.

Wrapper after extraction:

```python
def _populate_track_table(self, records: list[TrackRecord]) -> None:
    self._records_by_path = populate_library_table(
        self.tracks_table,
        records,
        item_factory=_table_item,
        format_missing_metadata=_format_missing_metadata,
        format_track_tags=_format_track_tags,
    )
    self._apply_song_filter(clear_selection=False)
```

### `populate_recommendation_table`

Signature:

```python
def populate_recommendation_table(
    table: QTableWidget,
    records: Sequence[TrackRecord],
    strategy_name: str,
    explanation: PlaylistExplanation | None,
    *,
    item_factory: TableItemFactory,
    format_track_tags: Callable[[TrackRecord], str],
    format_warning: Callable[[str], str],
) -> None:
    ...
```

Responsibilities:

- Set `table.setRowCount(len(records))`.
- Populate all existing recommendation columns with identical display text and sort values.
- Read transition data from `explanation.transitions` without modifying the explanation.
- Leave section expansion, workflow state, labels, and buttons to `MainWindow`.

Wrapper after extraction:

```python
def show_recommendation(
    self,
    records: list[TrackRecord],
    strategy_name: str,
    explanation: PlaylistExplanation | None = None,
) -> None:
    self._set_recommendation_sections_expanded(bool(records))
    populate_recommendation_table(
        self.recommendation_table,
        records,
        strategy_name,
        explanation,
        item_factory=_table_item,
        format_track_tags=_format_track_tags,
        format_warning=format_recommendation_warning,
    )
```

## Data flow

```text
MainWindow.show_tracks(records)
  -> MainWindow._populate_track_table(records)
     -> table_populators.populate_library_table(QTableWidget, records, formatters, item_factory)
        -> mutates only QTableWidget rows/items
        -> returns records_by_path
     -> MainWindow stores _records_by_path
     -> MainWindow reapplies active filters

MainWindow recommendation workflow
  -> MainWindow.show_recommendation(records, strategy, explanation)
     -> MainWindow expands/collapses recommendation sections
     -> table_populators.populate_recommendation_table(QTableWidget, records, strategy, explanation, formatters, item_factory)
        -> mutates only QTableWidget rows/items
```

## File changes

- `src/xfinaudio/desktop/table_populators.py`
  - New helper module with `populate_library_table`, `populate_recommendation_table`, and small private row/sort formatting helpers if useful.
- `src/xfinaudio/desktop/main_window.py`
  - Import the two helper functions.
  - Replace the body of `_populate_track_table` and the row-population body of `show_recommendation` with wrapper calls.
  - Keep `_SortAwareTableItem` and `_table_item` available and behavior unchanged.
- `tests/test_main_window.py` or a focused desktop table-populator test module
  - Add characterization coverage before extraction only if existing tests do not already pin the behavior being moved.

## Testing plan (strict TDD)

Test runner: `uv run pytest -q`.

Recommended first failing tests before implementation:

1. Library helper/wrapper preserves cells and mapping:
   - Build a `MainWindow` or a `QTableWidget` under offscreen Qt.
   - Populate complete and incomplete records.
   - Assert title, BPM, key, energy, missing metadata, genre, tags, status, and path cells match existing text.
   - Assert `_records_by_path[path]` maps to the original record through the `MainWindow._populate_track_table` wrapper.

2. Library sorting remains typed:
   - Preserve/extend the existing numeric BPM sorting coverage.
   - Ensure the wrapper still uses `_SortAwareTableItem` via the item factory seam.

3. Recommendation helper/wrapper preserves cells:
   - Populate records with an explanation containing a transition.
   - Assert strategy, path, transition score, and warning cells match current formatting.
   - Assert raw `PlaylistExplanation` warnings are not mutated.

Existing broad `tests/test_main_window.py` coverage should continue to run unchanged for construction, scanning, filtering, recommendation, export, Prep Copilot, compact layout, and offscreen behavior.

Validation after implementation:

- `uv run pytest -q`
- `uv run ruff check .`
- `uv run ruff format --check .`

## Rollout and rollback

Rollout is a single behavior-preserving refactor slice with no data migration or persistent format changes.

Rollback is straightforward: inline the helper calls back into `MainWindow._populate_track_table` and `MainWindow.show_recommendation`, then remove `table_populators.py`. Because wrappers and public contracts remain unchanged, rollback should not affect callers outside `main_window.py`.

## Risks and mitigations

- **Sort regressions:** Preserve the `_table_item` item factory seam and keep `_SortAwareTableItem` in use for every populated cell.
- **Filtering/selection regressions:** Return `_records_by_path` from `populate_library_table`; keep `_apply_song_filter(clear_selection=False)` in the `MainWindow` wrapper after table mutation.
- **Column drift:** Do not change headers or table construction. Helpers must populate cells in the exact current column order.
- **State/control regressions:** Keep recommendation section expansion and all labels/buttons in `MainWindow`; helper mutates only the target table.
- **Review budget overrun:** Defer panel builders, later table populators, and `WindowState` migration.

## Open decisions

No product decisions are required for this slice. The implementation should treat current behavior, including any quirky sort-value alignment, as the compatibility baseline unless a failing test exposes an existing bug and the user separately approves a bug-fix scope change.
