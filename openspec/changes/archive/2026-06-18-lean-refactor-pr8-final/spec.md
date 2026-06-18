# Spec: Slice main_window final

## ADDED Requirements

### Requirement: Factory methods must move to `window_factory.py`

The bodies of `MainWindow._initialize_library_controller`,
`MainWindow._replace_app_state`, `MainWindow._initialize_app_controller`, and
`MainWindow.with_defaults` MUST move to `src/xfinaudio/desktop/window_factory.py`
as `initialize_library_controller`, `replace_app_state`,
`initialize_app_controller`, and `with_defaults`.

#### Scenario: Window initialization still works

- **WHEN** `MainWindow.__init__` completes
- **THEN** all controllers, services, and state are initialized as before.

### Requirement: Settings apply must move to `settings_controller.py`

The body of `MainWindow._apply_settings` MUST move to
`src/xfinaudio/desktop/settings_controller.py` as
`SettingsController.apply_settings`.

#### Scenario: Settings apply still works

- **WHEN** the user changes a setting
- **THEN** the change is persisted, the export folder label is refreshed, and the
  language-change message box is shown if needed.

### Requirement: Prep copilot variant set must move to `prep_copilot.py`

The body of `MainWindow._set_applied_copilot_variant` MUST move to
`src/xfinaudio/desktop/prep_copilot.py` as
`PrepCopilotController.set_applied_variant`.

#### Scenario: Variant label still updates

- **WHEN** a copilot variant is applied
- **THEN** the applied variant label and tooltip are updated as before.

### Requirement: Small `_on_*` handlers must move to controllers

The ~16 small `_on_*` handler methods on `MainWindow` MUST move to
`src/xfinaudio/desktop/library_controller.py` (or a new tracks controller)
as methods on `LibraryController`.

#### Scenario: All UI handlers still work

- **WHEN** any UI event fires (track play, exclude, lock, clear constraints, etc.)
- **THEN** the appropriate controller method is called and the state updates as
  before.

### Requirement: `_LAYOUT_METHODS` dict must move to `layout.py`

The `_LAYOUT_METHODS` dict and the `setattr` loop that adds 47 methods to
`MainWindow` MUST move to `src/xfinaudio/desktop/layout.py` as
`install_layout_methods(target_class)`.

#### Scenario: All 47 methods still accessible

- **WHEN** code calls `main_window.choose_folder()` or any of the other 46
  methods
- **THEN** the call dispatches to the layout function as before.

### Requirement: 1-line shim methods must be removed

The 1-line shim methods on `MainWindow` (the `def name(self): self._foo.name()`
forwarders) MUST be removed. The call sites MUST be updated to call the
controller directly.

#### Scenario: Signal handlers still work

- **WHEN** any signal fires that was previously connected to a shim
- **THEN** the controller method is called and the behavior is unchanged.

## Invariants

- The full test suite (848 tests) MUST continue to pass unmodified.
- `main_window.py` after this PR MUST be under 400 LOC.
