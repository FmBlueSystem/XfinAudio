# Proposal: slim-main-window-qt-coordinator

## Intent

Slim `MainWindow` so it remains the public PySide6/Qt coordinator while behavior-preserving rendering responsibilities move into smaller, testable helpers. This is Change B of the existing refactor sequence, not a product feature and not a UX redesign.

The first implementation slice should extract library and recommendation table population logic from `MainWindow` while keeping all public widget attributes, method names, labels, table contents, sorting/filtering behavior, and application entry points unchanged.

## Scope

### First slice, preferred for <=400 changed lines

- Add a focused desktop table-populator module for library track and recommendation table rendering.
- Move row population and formatting loops currently embedded in:
  - `MainWindow._populate_track_table`
  - recommendation table body logic in `MainWindow.show_recommendation`
- Keep `MainWindow._populate_track_table` and `MainWindow.show_recommendation` as thin coordinator/wrapper methods.
- Preserve existing table contracts, including column order, hidden path/status behavior, sort-aware items, row counts, record lookup side effects, cell text, and enabled/disabled button state outcomes.
- Add or adjust characterization tests only where needed to lock down table cell text, row mapping, filtering, or sorting before refactoring.

### Later slices, explicitly deferred if needed

- Extract constructor/page/panel builders after table-rendering seams are stable.
- Migrate mutable `MainWindow` session fields to `WindowState` only after UI construction and display extraction are complete enough to reduce call-site risk.
- Consider additional display populators later for transition review, DJ readiness, Prep Copilot, and Serato export history.

## Non-goals

- No user-visible behavior changes.
- No changes to `app.py` or the public `MainWindow` entry-point contract.
- No redesign of tabs, layouts, labels, guidance text, table headers, or workflow copy.
- No broad state-model migration in this first slice.
- No background-worker, export, recommendation-domain, or metadata-scanning behavior changes.
- No implementation in this proposal phase.

## Affected areas

- `src/xfinaudio/desktop/main_window.py`: should lose table-rendering detail while retaining coordinator methods and public attributes.
- New or existing desktop helper module for table population/rendering.
- `tests/test_main_window.py` and related Qt/offscreen tests: should continue preserving construction, scan/recommend/export flows, filters/sorting, table headers/cells, readiness/review tables, persisted tracks, and worker behavior.
- Existing pure/domain helpers from Change A (`library_filter`, `export_coordinator`, `recommendation_presenter`, `_workers`) should remain compatible and not be reworked as part of this slice.

## Risks

- Table extraction can accidentally change exact cell text, column order, hidden column handling, row indexes, `_records_by_path`, or `_SortAwareTableItem` behavior.
- Sorting and filtering may regress if the extracted helper does not preserve existing item metadata and table setup assumptions.
- Recommendation rendering may regress if wrapper methods fail to preserve side effects beyond row insertion, such as selected/recommended state, explanations, or button states.
- A larger constructor or state extraction in the same PR could exceed the 400-line review budget and increase signal-wiring/object-lifetime risk.

## Rollback

Rollback should be straightforward because this is a behavior-preserving extraction: remove the new populator helper usage and restore the table population loops inside `MainWindow` wrappers. No data migrations, persistent schema changes, or external API changes are expected.

## Success criteria

- `MainWindow` remains the Qt coordinator and public desktop entry point.
- Library and recommendation table population responsibilities are moved out of `MainWindow` behind narrow helper functions/classes.
- Existing offscreen Qt behavior remains unchanged, including labels, headers, cell text, sorting/filtering, row counts, public attributes, and button-state outcomes.
- The first apply slice stays within the 400 changed-line review budget.
- Validation passes with the project commands from `openspec/config.yaml` (`uv run pytest -q`, `uv run ruff check .`, and `uv run ruff format --check .`) when implementation is later performed.
