# Exploration: slim-main-window-qt-coordinator

## Current state after Change A

- `MainWindow` remains the public Qt entry point and is still responsible for widget construction, layout assembly, signal wiring, table rendering, worker coordination, state updates, and export/recommendation orchestration.
- Change A helpers are already in use for pure/domain logic: `library_filter`, `export_coordinator`, `recommendation_presenter`, plus `_workers`. `window_state.py` exists as an immutable no-Qt state container, but `MainWindow` still stores equivalent mutable attributes directly (`selected_folder`, `scanned_records`, recommendation/export state).
- The constructor is the largest immediate hotspot: it creates every widget, configures table headers/selection, wires signals, builds all tab pages/layouts, applies visual design, and installs the central widget.
- Display population remains coupled to `MainWindow`: `_populate_track_table`, `_render_serato_export_history`, `_populate_prep_copilot_table`, `show_recommendation`, `_populate_dj_readiness_table`, and `show_transition_review` all format rows and mutate `QTableWidget`s directly.
- Existing `tests/test_main_window.py` strongly preserves public behavior through offscreen Qt tests: construction skeleton, initial guidance, scan/recommend/export flows, filters/sorting, table headers/cells, persisted tracks, readiness/review tables, and background workers.

## Target methods/classes for Change B

Recommended extraction targets that keep `MainWindow` as a Qt coordinator:

1. **Panel/page builders**
   - Extract constructor layout/page assembly into a desktop UI builder module or small builder class.
   - Candidate responsibilities: create top controls, library/build/review/export/metadata pages, workflow tabs, and central layout.
   - Keep public `MainWindow` widget attributes unchanged by returning/assigning the same named widgets used by tests (`folder_button`, `tracks_table`, `workflow_tabs`, etc.).

2. **Table/display populators**
   - Extract row-formatting/population helpers for:
     - library tracks: `_populate_track_table`
     - recommendation rows: `show_recommendation` table body
     - transition review: `show_transition_review`
     - DJ readiness: `_populate_dj_readiness_table`
     - Prep Copilot: `_populate_prep_copilot_table`
     - Serato history: `_render_serato_export_history`
   - Best seam: pure-ish functions/classes that accept `QTableWidget` + records/report/explanation and use shared `_table_item`/formatters, returning any needed indexes/maps separately.

3. **Optional later target, not first slice**
   - Move mutable session state to `WindowState` only after widget/layout and table-rendering seams are stable. This touches many call sites and risks exceeding the review budget.

## Risks and constraints

- Public `MainWindow` API and tested widget attributes must remain unchanged; `app.py` must not change.
- Strict TDD is active: apply phase should add/update failing characterization tests before implementation.
- Qt tests run offscreen only; refactor should avoid visual/behavioral changes that need manual UI QA.
- Constructor extraction can silently break signal wiring or object lifetime if builder-created widgets/layouts are not attached to `MainWindow`/central widget correctly.
- Table extraction can break sorting/filtering because current tables rely on `_SortAwareTableItem`, hidden path/status columns, exact column order, row indexes, and `_records_by_path`.
- Existing tests assume exact labels, guidance strings, column headers, row counts, button enabled states, and public attributes.
- Keep slices under the 400 changed-line review budget; avoid broad state-model migration in the same PR.

## Recommended first slice (<=400 changed lines)

Start with a narrow, high-value display extraction rather than constructor/page extraction:

1. Add a table-populator module for library and recommendation table rendering only.
2. Move row/header-independent formatting loops from `_populate_track_table` and `show_recommendation` into functions that accept the existing `QTableWidget` and existing formatter callbacks/constants.
3. Keep `MainWindow._populate_track_table` and `MainWindow.show_recommendation` as thin wrappers so the public API and tests stay stable.
4. Add/adjust characterization tests around library and recommendation table cell text/sorting if needed, then preserve all existing `test_main_window.py` behavior.
5. Defer constructor panel builders to the next slice, because that touches many widgets/signals/layouts at once.

This first slice slims meaningful code from `MainWindow`, has clear offscreen-test coverage, and avoids state/API changes.
