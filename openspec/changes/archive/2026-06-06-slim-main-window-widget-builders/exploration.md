# Exploration: slim-main-window-widget-builders

## Scope

Behavior-preserving next slice for `xfinaudio.desktop.main_window.MainWindow` after archived changes:

- `slim-main-window-qt-coordinator`
- `slim-main-window-panel-builders` PR 1

Inputs reviewed:

- `openspec/config.yaml`
- `openspec/specs/desktop-main-window/spec.md`
- Archived exploration/tasks/apply/verify artifacts for both prior changes
- `src/xfinaudio/desktop/main_window.py`
- `src/xfinaudio/desktop/table_populators.py`
- `tests/test_main_window.py`
- `tests/test_table_populators.py`

## Current state

- `MainWindow` remains the public desktop coordinator and `xfinaudio.desktop.app:main` compatibility is preserved by the existing spec.
- Previous table extraction is already in place via `populate_library_table` and `populate_recommendation_table`; table populator tests cover those helpers.
- The archived panel-builder PR 1 completed only state and signal extraction:
  - `_initialize_window_state(...)` now owns constructor dependency/runtime state setup.
  - `_connect_widget_signals()` now owns constructor signal/table-sort wiring.
- The constructor still directly contains two large behavior-sensitive blocks:
  - Widget creation and intrinsic widget state: about 110 lines (`setWindowTitle`, public widget attributes, labels, headers, enabled states, selection modes, word wrap/sizing).
  - Layout/page/tab assembly: about 105 lines (controls, page layouts, `workflow_tabs`, central widget, compact layout call).

## Recommended next focused slice

Create a proposal for extracting widget creation/intrinsic widget state into a private `MainWindow._build_widgets() -> None` method.

Recommended change name: `slim-main-window-widget-builders`.

Apply boundary should be narrow:

1. Keep `MainWindow.__init__` as the public construction coordinator.
2. Move only the existing widget construction/configuration block into `_build_widgets()`:
   - window title
   - all public widget attribute assignments
   - table header setup
   - table selection behavior/mode setup
   - initial enabled/visible states
   - label word-wrap/size constraints
3. Call `_build_widgets()` after `_initialize_window_state(...)` and before `_connect_widget_signals()`.
4. Preserve the existing ordering around `_connect_widget_signals()`, `_apply_visual_design()`, layout assembly, and `_apply_compact_mac_layout(...)`.
5. Do not extract central/page layout assembly in this slice.
6. Do not touch table population, worker coordination, export/recommendation behavior, app entrypoint, or product copy/UX.

## Why this slice

- It follows the archived PR chain recommendation exactly: PR 2 should extract widget creation/intrinsic widget state before PR 3 central/page layout extraction.
- It is smaller and safer than extracting layout/page builders now because it does not change Qt layout ownership or page hierarchy.
- Existing constructor characterization already covers the widget attributes, table headers, labels, tab contract, and important initial hidden/enabled states that must survive the move.
- The likely changed-line footprint is comfortably below the 400-line review budget because the slice is mostly move-only within `main_window.py` plus optional small characterization additions.

## Existing coverage relevant to this slice

Strong existing coverage in `tests/test_main_window.py`:

- `test_main_window_constructor_exposes_initial_panel_contract`
- `test_main_window_constructs_desktop_scanning_skeleton`
- `test_main_window_displays_initial_empty_state_guidance`
- `test_main_window_initial_flow_disables_invalid_next_actions`
- visual/layout smoke tests including compact table sizes, hidden empty recommendation sections, workflow tab names/position, and object names
- scan/filter/recommend/export flow tests that depend on the same public widget attributes after construction

Potential proposal/apply test addition, if desired: one focused assertion group for selection modes/behaviors on `tracks_table` and `prep_copilot_table`, because those are intrinsic widget settings in the proposed moved block.

## Affected files forecast

Expected apply files:

- `src/xfinaudio/desktop/main_window.py`
- `tests/test_main_window.py` only if adding the optional selection-mode characterization
- `openspec/changes/slim-main-window-widget-builders/` for proposal/spec/design/tasks in later phases

Files intentionally not affected:

- `src/xfinaudio/desktop/app.py`
- `src/xfinaudio/desktop/table_populators.py`
- `src/xfinaudio/desktop/_workers.py`
- export/recommendation/library domain modules

## Risks / watch points

- `_build_widgets()` must run before `_connect_widget_signals()` because signal wiring assumes every widget attribute exists.
- `_build_widgets()` must also run before `_apply_visual_design()` because visual design sets object names and table defaults on created widgets.
- Keep `tracks_table.itemSelectionChanged.connect(self._refresh_idle_action_state)` in `_connect_widget_signals()` rather than leaving a stray connection inside `_build_widgets()`, unless the proposal explicitly accepts that exception.
- `safe_export_folder_label` depends on `_format_safe_export_folder_label()`, which reads initialized settings; preserve `_initialize_window_state()` first.
- `serato_export_history_table` starts hidden before compact layout; `prep_copilot_table`, `recommendation_table`, `transition_review_table`, and `dj_readiness_table` become hidden through existing compact/recommendation-section side effects. Preserve these states.
- Avoid broad formatting churn; this slice should be a mechanical extraction, not a copy/layout redesign.

## Ready for proposal

Yes. The next slice is focused, behavior-preserving, already supported by characterization coverage, and should fit the review budget.
