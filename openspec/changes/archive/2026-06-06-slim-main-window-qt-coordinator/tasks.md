# Tasks: slim-main-window-qt-coordinator

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 180-300 for first table-populator slice; full Change B likely >400 |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | Single PR: table populators only; defer constructor/panel extraction |
| Delivery strategy | single-pr |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Medium

## Apply Slice Boundary

This apply slice is limited to extracting library and recommendation table population into `src/xfinaudio/desktop/table_populators.py`. Do not extract constructor/page/panel builders, move `WindowState`, alter workers, or change UX/copy in this slice.

## Implementation Tasks

- [x] RED library populator: add focused failing tests in `tests/test_table_populators.py` for `populate_library_table` using an offscreen `QTableWidget`, representative `TrackRecord` fixtures, a simple item factory, and formatter callbacks; assert the 10 library columns, returned `{path: record}` mapping, and numeric BPM sort-value behavior; focused validation target is `uv run pytest -q tests/test_table_populators.py -k library`.
- [x] GREEN library populator: create `src/xfinaudio/desktop/table_populators.py` with `TableItemFactory` and `populate_library_table(...)`, moving only library row value and sort-value construction from `MainWindow._populate_track_table` while preserving existing column order, text formatting, and sort-value quirks.
- [x] REFACTOR library populator: keep helper imports narrow, avoid importing `src/xfinaudio/desktop/main_window.py`, and leave `_SortAwareTableItem`, `_table_item`, `_format_missing_metadata`, and `_format_track_tags` in `main_window.py` for explicit injection.
- [x] RED library wrapper: add or adjust `tests/test_main_window.py` coverage for `MainWindow._populate_track_table` or `show_tracks` asserting `_records_by_path[path]` maps to the original record, active filters are re-applied with `clear_selection=False`, and existing BPM sorting or sorted-row selection coverage still exercises the wrapper path; focused validation target is `uv run pytest -q tests/test_main_window.py -k "populate_track_table or sorts_library_bpm or sorted_selection or filter"`.
- [x] GREEN library wrapper: import `populate_library_table` in `src/xfinaudio/desktop/main_window.py` and replace the body of `_populate_track_table` with a thin wrapper that assigns the returned mapping to `self._records_by_path` and then calls `_apply_song_filter(clear_selection=False)`.
- [x] REFACTOR library wrapper: remove only now-dead library row-loop code from `src/xfinaudio/desktop/main_window.py` and verify no public widget attributes, table headers, filtering behavior, or wrapper method signatures changed.
- [x] RED recommendation populator: extend `tests/test_table_populators.py` with failing `populate_recommendation_table` coverage using records plus a `PlaylistExplanation` with one transition; assert the 11 recommendation columns, blank first-row transition fields, `final_score:.3f`, formatted warnings joined by `"; "`, and no mutation of raw explanation warnings; focused validation target is `uv run pytest -q tests/test_table_populators.py -k recommendation`.
- [x] GREEN recommendation populator: implement `populate_recommendation_table(...)` in `src/xfinaudio/desktop/table_populators.py`, reading `explanation.transitions` without mutation and using injected `item_factory`, `format_track_tags`, and `format_warning` callbacks.
- [x] REFACTOR recommendation populator: keep section expansion, labels, buttons, recommendation workflow state, review tables, DJ readiness, Prep Copilot, export, and worker behavior out of `table_populators.py`; the helper must mutate only the passed `QTableWidget`.
- [x] RED recommendation wrapper: add or adjust `tests/test_main_window.py` coverage for `MainWindow.show_recommendation` asserting recommendation rows, warning formatting, section expansion, and existing button/state outcomes remain observable through the public wrapper; focused validation target is `uv run pytest -q tests/test_main_window.py -k "show_recommendation or recommendation_table or warning_cells"`.
- [x] GREEN recommendation wrapper: import `populate_recommendation_table` in `src/xfinaudio/desktop/main_window.py` and replace only the recommendation table row-population loop in `show_recommendation` with the helper call after `_set_recommendation_sections_expanded(bool(records))`.
- [x] REFACTOR recommendation wrapper: remove only now-dead recommendation row-loop code from `src/xfinaudio/desktop/main_window.py` and verify recommendation review, DJ readiness, Prep Copilot, export, worker behavior, labels, and control states are unchanged.
- [x] Full regression: run `uv run pytest -q`, `uv run ruff check .`, and `uv run ruff format --check .`; fix only behavior-preserving issues in `src/xfinaudio/desktop/table_populators.py`, `src/xfinaudio/desktop/main_window.py`, or focused tests from this apply slice.
- [x] Review-budget gate: inspect the final diff and confirm it stays near the 180-300 changed-line forecast; if it approaches or exceeds 400 changed lines, stop before expanding scope and ask for delivery guidance.

## Future Tasks (Deferred; not part of this apply slice)

These deferred items are intentionally not unchecked implementation checkboxes for this apply slice.

- Deferred: extract constructor/page/panel builders from `src/xfinaudio/desktop/main_window.py` only after table-populator extraction is merged and stable.
- Deferred: consider later display populators for transition review, DJ readiness, Prep Copilot, and Serato export history in separate review-budgeted slices.
- Deferred: migrate mutable session fields to `WindowState` only after UI construction and display extraction reduce call-site risk.
