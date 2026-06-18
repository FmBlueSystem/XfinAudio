# Spec: Slice main_window shell

## ADDED Requirements

### Requirement: AppController must own state sync and render orchestration

A new `AppController` class MUST live in `src/xfinaudio/desktop/app_controller.py`.
It MUST own:
- `sync_state()` — replaces `MainWindow._sync_state`
- `render_screens()` — replaces `MainWindow._render_screens`
- `render_tab(index, lightweight)` — replaces `MainWindow._render_tab`
- `refresh_state_fields()` — replaces `MainWindow._refresh_state_fields`
- `on_tab_changed(index)` — replaces `MainWindow._on_tab_changed`
- `update_tab_states()` — replaces `MainWindow._update_tab_states`

`MainWindow` MUST call the controller via one-line shims. The signal
`workflow_tabs.currentChanged` MUST still be wired in `MainWindow` to
`self.on_tab_changed` (shim → controller).

#### Scenario: State sync still updates all screens

- **WHEN** `MainWindow._sync_state()` is called
- **THEN** `AppController.sync_state()` runs and every render-driven screen
  reflects the latest `AppState`.

### Requirement: LibraryController must own library state and spectral worker

A new `LibraryController` class MUST live in
`src/xfinaudio/desktop/library_controller.py`. It MUST own the 17 methods
listed in the proposal. `MainWindow` MUST call the controller via one-line
shims. The signals from `LibraryScreen` (folder_change_requested,
scan_requested, etc.) MUST still be wired in `MainWindow` to the
`MainWindow.<method>` shim, which forwards to the controller.

#### Scenario: Folder selection still propagates

- **WHEN** the user picks a folder via the file dialog
- **THEN** the folder label, guidance labels, and idle action state all
  update as before.

#### Scenario: Spectral completion worker still runs after scan

- **WHEN** a scan completes
- **THEN** the spectral completion worker starts, updates progress, and
  fills in missing spectral profiles, exactly as before.

### Requirement: SettingsController must own settings dialog and apply

A new `SettingsController` class MUST live in
`src/xfinaudio/desktop/settings_controller.py`. It MUST own:
- `open_settings_dialog()` — replaces `MainWindow._open_settings_dialog`
- `on_spectral_cohesion_changed(value)` — replaces `MainWindow._on_spectral_cohesion_changed`
- `apply_settings(new_settings)` — replaces `MainWindow._apply_settings`
- `format_safe_export_folder_label()` — replaces `MainWindow._format_safe_export_folder_label`

`MainWindow` MUST call the controller via one-line shims. The
`_settings_dialog` instance stays on `MainWindow` so the language-change
message box can be shown from the right parent.

#### Scenario: Settings dialog still applies and persists

- **WHEN** the user changes a setting in the dialog
- **THEN** the change is persisted to the settings repository and the
  export folder label is refreshed.

### Requirement: DjReadinessController must own readiness display

A new `DjReadinessController` class MUST live in
`src/xfinaudio/desktop/dj_readiness_controller.py`. It MUST own:
- `show(recommendation, quality_report, *, serato_plan, serato_volume_root)` — replaces `MainWindow._show_dj_readiness`
- `populate_table(report)` — replaces `MainWindow._populate_dj_readiness_table`

`MainWindow` MUST call the controller via one-line shims.

#### Scenario: DJ readiness report still renders

- **WHEN** the recommendation service emits a completion
- **THEN** the readiness label and table are updated, and the report is
  stored on `MainWindow.last_dj_readiness_report`.

## MODIFIED Requirements

None.

## REMOVED Requirements

None.

## Invariants

- The full test suite (848 tests) MUST continue to pass unmodified. Imports
  MAY be updated; assertions MUST NOT.
- `main_window.py` after this PR MUST be under 600 LOC.
- All 4 controllers MUST take their dependencies explicitly via constructor
  injection. No Protocol-with-one-impl host types.
- The 15 property accessors on `MainWindow` (workflow_service,
  selected_folder, scanned_records, last_*, etc.) STAY on `MainWindow`. They
  are NOT moved to AppState in this PR.
- The signal wiring in `_connect_widget_signals` does NOT change in shape.
  The targets are still `MainWindow.<method>` shims.
