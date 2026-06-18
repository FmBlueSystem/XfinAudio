# Spec: Slice main_window.py (partial)

## ADDED Requirements

### Requirement: Layout helper must live in its own module

`responsive_sidebar_width(window_width: int) -> int` MUST live in
`src/xfinaudio/desktop/layout.py`. `MainWindow` MUST import it from there.

#### Scenario: Layout helper is importable

- **WHEN** `from xfinaudio.desktop.layout import responsive_sidebar_width` is invoked
- **THEN** the import succeeds and the function returns the same value as before.

### Requirement: WorkflowStack must live in its own module

`WorkflowStack(QStackedWidget)` MUST live in
`src/xfinaudio/desktop/workflow_stack.py`. `MainWindow` MUST import it from there.
The class MUST continue to expose `tabText`, `setTabEnabled`, `isTabEnabled`,
`setCurrentIndex`, and `currentChanged`.

#### Scenario: WorkflowStack is importable

- **WHEN** `from xfinaudio.desktop.workflow_stack import WorkflowStack` is invoked
- **THEN** the import succeeds.

### Requirement: SettingsPersistence Protocol must move to app_state.py

`SettingsPersistence` Protocol MUST live in
`src/xfinaudio/desktop/app_state.py`. `MainWindow` MUST import it from there.

#### Scenario: Protocol is importable

- **WHEN** `from xfinaudio.desktop.app_state import SettingsPersistence` is invoked
- **THEN** the import succeeds.

### Requirement: UndoToolbar must encapsulate undo UI

A new `UndoToolbar` class MUST live in `src/xfinaudio/desktop/undo_toolbar.py`.
It MUST expose `undo()` and `redo()` methods. `MainWindow` MUST delegate its
existing `undo`/`redo`/`_refresh_undo_state` logic to this class.

#### Scenario: UndoToolbar is wired correctly

- **WHEN** `UndoToolbar(undo_manager, parent).toolbar` is added to the main window
- **THEN** the undo and redo buttons reflect the `UndoManager` state and calling
  `undo()` / `redo()` updates the toolbar.

### Requirement: Shortcuts wiring must be a free function

`bind_main_window_shortcuts(window)` MUST live in
`src/xfinaudio/desktop/shortcuts.py`. It MUST register the same 11 shortcuts
that `_connect_keyboard_shortcuts` registers today.

#### Scenario: All 11 shortcuts are bound

- **WHEN** `bind_main_window_shortcuts(window)` returns
- **THEN** the shortcut registry has 11 entries with the same names as before.

### Requirement: ResponsiveLayout must encapsulate resize logic

A new `ResponsiveLayout` class MUST live in
`src/xfinaudio/desktop/responsive.py`. It MUST own the sidebar panel, the
sidebar list, the label list, and the responsive width callback. `MainWindow`
MUST delegate `resizeEvent`, `_apply_responsive_layout`, and `set_full_screen`
to it.

#### Scenario: Resize still adjusts the sidebar

- **WHEN** the window is resized to a width that triggers narrow-mode
- **THEN** the sidebar collapses to icons, same as before.

### Requirement: Visual design must be a free function

`apply_visual_design(window)` MUST live in
`src/xfinaudio/desktop/visual_design.py`. It MUST apply the same dark theme,
compact mac layout, table column widths, and `objectName`s that
`_apply_compact_mac_layout` + `_apply_compact_table_columns` +
`_apply_visual_design` apply today.

#### Scenario: Visual design is applied

- **WHEN** `apply_visual_design(window)` returns
- **THEN** the window's stylesheet is set, the table column widths are
  configured, and the primary-action button has the right `objectName`.

### Requirement: Table sorting must be a free function

`connect_table_sorting(table, sort_orders, on_library_resort)` MUST live in
`src/xfinaudio/desktop/table_sorting.py`. `MainWindow` MUST call it for each
of the 4 tables it currently wires.

#### Scenario: All 4 tables are sortable

- **WHEN** the user clicks a column header on any of the 4 tables
- **THEN** the column sorts in the same way as before, and a re-sort of the
  library table re-runs the song filter.

### Requirement: Prep copilot state machine must be a controller

A new `PrepCopilotController` class MUST live in
`src/xfinaudio/desktop/prep_copilot.py`. It MUST own the `generate_prep_copilot`,
`apply_selected_prep_copilot_variant`, `_apply_prep_copilot_item`, and
`_on_copilot_variant_applied` methods. `MainWindow` MUST delegate these to
the controller.

#### Scenario: Prep copilot still works

- **WHEN** the user clicks the prep copilot button on the build screen
- **THEN** the controller runs the same workflow as before and the build
  screen shows the same table.

### Requirement: Recommendation rendering must be a free function

`render_recommendation(host, state, view_models)` MUST live in
`src/xfinaudio/desktop/recommendation_render.py`. `MainWindow` MUST delegate
`show_recommendation`, `clear_recommendation_review`, and
`show_transition_review` to it.

#### Scenario: Recommendation rendering still works

- **WHEN** the recommendation service emits a completion
- **THEN** the review screen shows the same ordered tracks, summary, and
  transition review as before.

### Requirement: Export thin wrappers must be a facade

A new `ExportActions` class MUST live in
`src/xfinaudio/desktop/export_actions.py`. It MUST delegate the 8 export
methods to `ExportCoordinator`. `MainWindow` MUST route those calls through
the facade.

#### Scenario: All export actions still work

- **WHEN** the user previews or exports a recommendation
- **THEN** the same `ExportCoordinator` methods are called and the same
  side effects (status label, history, sidecars) occur.

## MODIFIED Requirements

None.

## REMOVED Requirements

None.

## Invariants

- The full test suite (848 tests after PR 4) MUST continue to pass
  unmodified. Imports MAY be updated; assertions MUST NOT.
- `main_window.py` after this PR MUST be under 1100 LOC.
- The public method names on `MainWindow` that the coordinators and services
  call (`selected_folder`, `scanned_records`, `last_recommendation`, etc.)
  MUST stay the same.
- `app_state.py` is extended (with `SettingsPersistence`); it is not replaced.
