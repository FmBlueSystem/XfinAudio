## Why

`src/xfinaudio/desktop/main_window.py` is 1770 LOC with 140 methods, 57 imports, and
a single `MainWindow` class that owns: window state, layout, responsive resize, undo
toolbar, keyboard shortcuts, signal wiring, table sorting, visual design, plus 30+
public action methods that mostly delegate to coordinators. It is the largest single
file in the codebase and the only one still over the 400-line review budget.

This PR extracts the obvious standalone chunks into their own modules. It does NOT
attempt to fully split `MainWindow` into a 4-class shell — that is a follow-up.

## What changes

### Pure extractions to new modules (10)

1. **`responsive_sidebar_width` helper** → `src/xfinaudio/desktop/layout.py`
   (17 LOC). Pure function, no Qt state. Already used by `_apply_responsive_layout`.
2. **`WorkflowStack` (QStackedWidget subclass)** → `src/xfinaudio/desktop/workflow_stack.py`
   (28 LOC). Small wrapper that exposes only the navigation-relevant methods.
3. **`SettingsPersistence` Protocol** → merge into `src/xfinaudio/desktop/app_state.py`
   (5 LOC). It declares one method (`save`) used by `_persist_window_geometry` and
   `with_defaults`; it can live next to the AppState definitions.
4. **Undo toolbar construction + `undo`/`redo`/`_refresh_undo_state`** → new
   `src/xfinaudio/desktop/undo_toolbar.py` (~50 LOC). A small `UndoToolbar` class
   that takes the `UndoManager` and the parent window, builds the QToolBar, and
   exposes `undo()`/`redo()` methods.
5. **Keyboard shortcuts wiring (`_connect_keyboard_shortcuts`)** → new
   `src/xfinaudio/desktop/shortcuts.py` (~40 LOC). A `bind_main_window_shortcuts(window)`
   function that builds the 11 shortcuts.
6. **Responsive resize logic (`resizeEvent`, `_apply_responsive_layout`,
   `set_full_screen`)** → new `src/xfinaudio/desktop/responsive.py` (~50 LOC).
   A `ResponsiveLayout` class that takes the sidebar panel, the sidebar list, the
   label list, and a width callback.
7. **Visual design setup (`_apply_compact_mac_layout`,
   `_apply_compact_table_columns`, `_apply_visual_design`)** → new
   `src/xfinaudio/desktop/visual_design.py` (~110 LOC). A `apply_visual_design(window)`
   function that takes a `MainWindow` and applies all the design tokens.
8. **Table sorting (`_connect_table_sorting`, `_sort_table_by_column`)** → new
   `src/xfinaudio/desktop/table_sorting.py` (~30 LOC). A `connect_table_sorting(table,
   sort_orders, on_library_resort)` function.
9. **Prep copilot state machine (`generate_prep_copilot`,
   `apply_selected_prep_copilot_variant`, `_apply_prep_copilot_item`,
   `_on_copilot_variant_applied`)** → new `src/xfinaudio/desktop/prep_copilot.py`
   (~140 LOC). A `PrepCopilotController` that takes the `BuildScreen`,
   `BuildViewModel`, `AppState`, the `workflow_service`, and a callback to refresh
   state.
10. **Recommendation rendering (`show_recommendation`,
    `clear_recommendation_review`, `show_transition_review`)** → new
    `src/xfinaudio/desktop/recommendation_render.py` (~140 LOC). A
    `render_recommendation(host, view_models, state)` function with the same
    signature as the current MainWindow methods, returning a small DTO.
11. **Export thin wrappers (`export_dj_readiness_report`, `preview_export`,
    `export_recommendation`, `preview_serato_export`,
    `export_recommendation_to_serato`, `export_metadata_status_to_serato`,
    `choose_safe_export_folder`, `set_safe_export_folder`)** → new
    `src/xfinaudio/desktop/export_actions.py` (~110 LOC). A small facade that
    delegates to `ExportCoordinator`.

### Things explicitly NOT in this PR (residual)

- The `MainWindow` class itself remains the single source of truth for the
  application window, signal wiring, and the `_sync_state`/`_render_screens`
  orchestration. After this PR, `main_window.py` will be ~1020 LOC — still
  over the 400-line budget, but ~40% smaller.
- The AppState property accessors (lines 543-665) STAY on `MainWindow` because
  moving them to `AppState` directly would change the public attribute access
  pattern used by 50+ call sites in `main_window`, the services, the
  coordinators, and the tests. That refactor is a separate concern.
- The signal wiring method `_connect_widget_signals` stays on `MainWindow`
  because it is genuinely cross-cutting: it touches 7 screens, the scan and
  recommendation services, the playlist coordinator, the audio player, the
  menu, and the keyboard shortcuts.

## Non-goals

- Reducing `main_window.py` below 400 LOC. That requires a much larger
  refactor (splitting `MainWindow` into `MainWindowShell` + 4 screen-owned
  controllers + 1 app-state controller), which would touch every screen and
  is not feasible in a single PR.
- Renaming `MainWindow` to `MainWindowShell` or similar.
- Moving property accessors to `AppState`.

## Impact

- Net: ~750 LOC moved out of `main_window.py`; new main_window: ~1020 LOC.
- New files: 10 (one per extraction).
- Imports removed from `main_window.py`: ~15 (the `from .layout import …` style
  stays because the function is now in a sibling module; a couple of helper
  imports go away).
- Review budget: this PR exceeds the 400-line cap on **changed lines** (we are
  adding 10 new files and removing ~750 LOC from one). The change set is large
  in surface area but small in *behavior* (zero new behavior, all tests pass).
  This is the documented residual; see "Follow-up" below.
- Risk: medium-high. Many small method extractions with a long test surface.
  Strict TDD applies: the existing test suite is the contract.

## Follow-up

A follow-up PR (`refactor/slice-mainwindow-residual`) should:

- Extract `MainWindow` into `MainWindowShell` + a `StateController` +
  per-screen controllers.
- Move the AppState property accessors into `AppState` directly.
- Reduce `main_window.py` to under 400 LOC.

This is documented in the `lean-refactor` follow-up backlog (not yet created;
this PR will create it).
