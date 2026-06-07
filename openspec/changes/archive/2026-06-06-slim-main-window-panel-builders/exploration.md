# Exploration: slim-main-window-panel-builders

## Scope

Behavior-preserving extraction of `MainWindow.__init__` widget/control/page construction for `xfinaudio.desktop.main_window.MainWindow`.

Inputs reviewed:

- `openspec/config.yaml`
- `openspec/specs/desktop-main-window/spec.md`
- `src/xfinaudio/desktop/main_window.py`
- `src/xfinaudio/desktop/table_populators.py`
- Relevant `tests/test_main_window.py` and `tests/test_table_populators.py` coverage

## Current state

- `MainWindow` remains the public desktop coordinator and entrypoint target remains `xfinaudio.desktop.app:main`.
- `main_window.py` is large: 1,669 lines. The constructor is the next obvious slimming target: it builds runtime state, all public widgets, signal connections, page layouts, tabs, compact layout, and central widget in one method.
- Previous table-populator extraction is already in place via `xfinaudio.desktop.table_populators.populate_library_table` and `populate_recommendation_table`.
- Existing tests heavily characterize public widget attributes, labels, headers, initial enabled states, hidden/visible review sections, tab names/position, layout sizing, table column widths, styling object names, and public wrapper behavior.

## Constructor responsibilities to preserve

The constructor currently performs these behavior-sensitive groups:

1. Runtime/session state
   - `workflow_service`, settings, selected folder, scanned/recommendation/readiness/copilot state, worker refs, export history, sort state, search state.
2. Primary scan controls
   - Folder/scan/cancel buttons, folder/guidance/progress/status labels, initial enabled states.
3. Library filters and table
   - `song_search_input`, status/missing filters, metadata export button, `tracks_table` headers, selection behavior/mode, selection-change signal.
4. Recommendation/build controls
   - `strategy_combo`, recommend button, prep copilot inputs/buttons/table, recommendation table headers.
5. Review/export/metadata widgets
   - Review summary/readiness labels/tables, transition review table, Serato history table, export buttons/labels, decision labels.
6. Label sizing/wrapping and signal wiring
   - Button clicks, text/filter changes, prep table double-click, export lambdas, table sorting connections.
7. Page/layout assembly
   - Command bar, Library, Build Playlist, Review Mix, Export to Serato, Metadata Worklist pages; west-positioned `workflow_tabs`; central layout and compact Mac layout.
8. Visual/compact layout side effects
   - `_apply_visual_design()`, `_apply_compact_mac_layout(...)`, and `_set_recommendation_sections_expanded(False)` through compact layout.

## Relevant existing test coverage

Strong coverage already exists for the first slice:

- Construction basics: `test_main_window_constructs_desktop_scanning_skeleton`
- Initial labels and disabled actions: `test_main_window_displays_initial_empty_state_guidance`, `test_main_window_initial_flow_disables_invalid_next_actions`
- Layout/style: `test_main_window_applies_dj_visual_style`, `test_main_window_uses_compact_macbook_layout_for_library_section`, `test_main_window_collapses_empty_recommendation_sections_to_prioritize_browsing`, `test_main_window_uses_two_row_responsive_command_bars_for_mac_resolution`
- Initial hidden sections: `test_main_window_empty_review_hides_empty_result_tables`
- Tab/page contract: `test_main_window_exposes_dj_workflow_modules_with_decision_points`
- Library/recommendation headers and data: many `show_tracks`, `show_recommendation`, filtering, sorting, and recommendation tests
- Entrypoint compatibility: `test_desktop_app.py` and `test_pyinstaller_packaging.py` monkeypatch `MainWindow.with_defaults`

Potential gap before apply: a single focused characterization can snapshot constructor-created public widget attributes, table headers, and key initial enabled/hidden states in one place. It should not assert private helper names unless the team wants implementation-shape TDD.

## Recommended first apply slice (<400 changed lines)

Prefer private `MainWindow` builder methods over a helper module. This keeps Qt parent ownership, signal wiring, and public attributes on `self` unchanged.

Suggested slice:

1. Add/adjust one focused constructor characterization test (small, behavior-level):
   - Assert public tables expose exact headers for `tracks_table`, `recommendation_table`, `prep_copilot_table`, `transition_review_table`, `serato_export_history_table`, `dj_readiness_table`.
   - Assert initial important button states (`scan`, `cancel`, `recommend`, export, prep apply) and hidden tables remain unchanged.
   - Assert workflow tab names/position remain unchanged.
2. Extract within `MainWindow` only:
   - `_initialize_window_state(...) -> None`
   - `_build_static_widgets() -> None` or smaller `_build_scan_widgets`, `_build_library_widgets`, `_build_recommendation_widgets`, `_build_review_widgets`, `_build_export_widgets`, `_build_metadata_widgets`
   - `_connect_widget_signals() -> None`
   - `_build_central_widget() -> QWidget`
3. Keep all public widget attributes assigned on `self` with the same names and before methods that consume them.
4. Keep `_apply_visual_design()` before compact layout as today, and keep `_apply_compact_mac_layout(...)` after root layout/tabs are assembled as today.
5. Do not move table population, recommendation rendering, worker coordination, export behavior, or app entrypoint in this slice.

Estimated changed lines:

- Test characterization: ~30-60 changed lines.
- Constructor extraction: mostly moving existing code plus method shells; likely ~250-340 changed lines if kept to 3-5 helpers and no copy/style churn.
- Total should remain under the 400 changed-line review budget if the extraction avoids broad reformatting.

## Safer extraction shape

Recommended method boundaries for minimal risk:

- `__init__`: orchestrates only state init, widget init, signal wiring, central widget creation.
- `_initialize_window_state(scan_service, repository, settings, settings_repository)`: non-Qt/session state.
- `_build_widgets()`: creates every public widget attribute and sets headers, initial labels, enabled states, wrapping, sizing that is intrinsic to the widget.
- `_connect_widget_signals()`: exactly the existing signal wiring block plus table sorting loop.
- `_build_main_layout() -> QVBoxLayout`: creates local layouts/pages/tabs and returns root layout.

This is safer than returning many individual widgets from standalone helpers because tests and downstream code rely on `window.<attribute>` names.

## Risks / watch points

- Signal wiring order matters: `tracks_table.itemSelectionChanged` must still connect to `_refresh_idle_action_state`; text/filter changes must still reapply filters; table header sorting must still be connected after all tables exist.
- Visual/compact side effects depend on all widgets and layouts existing. Preserve order around `_apply_visual_design()` and `_apply_compact_mac_layout(...)`.
- `selected_folder` is assigned twice today: initialized to `None`, then assigned from `self.settings.library.last_scan_folder`. Preserve the effective final value and avoid calling `set_selected_folder()` during construction, because that would clear saved-library state and persist settings.
- `serato_export_history_table` starts hidden before layout and remains covered by existing tests.
- `prep_copilot_table` is hidden by `_apply_compact_mac_layout`; preserve that side effect.
- Avoid changing `table_populators.py` in this slice. It has existing behavior (including sort-value details) covered by tests and is outside the constructor-builder target.

## Validation commands

From `openspec/config.yaml`:

- `uv run pytest -q`
- `uv run ruff check .`
- `uv run ruff format --check .`

## Recommendation

Proceed to proposal/design/tasks for a narrow constructor-builder refactor. The first apply slice should be private `MainWindow` methods only, with no public API or UX change and no separate helper module unless a later slice identifies a genuinely reusable Qt panel factory boundary.
