# Spec: Slice main_window residual

## ADDED Requirements

### Requirement: Signal wiring must move to per-screen `connect_signals`

Each screen (`LibraryScreen`, `BuildScreen`, `ReviewScreen`, `ExportScreen`,
`MetadataScreen`, `LiveAssistantScreen`, `MyPlaylistsScreen`, `PlaylistEditor`)
MUST expose a `connect_signals(window)` method that connects its own signals
to the appropriate slots on the window (or its controllers).

`MainWindow` MUST call each screen's `connect_signals` in its constructor (after
the screens and controllers are constructed). The old `_connect_widget_signals`
method on `MainWindow` MUST be removed.

#### Scenario: All screen signals still connect

- **WHEN** `MainWindow.__init__` completes
- **THEN** every signal that was previously connected in `_connect_widget_signals`
  is still connected to its previous slot.

### Requirement: `build_layout` and `build_widgets` must live in `layout.py`

The body of `MainWindow._build_layout` and `MainWindow._build_widgets` MUST
move to `src/xfinaudio/desktop/layout.py` as `build_main_window_layout(window)`
and `build_main_widgets(window)`.

`MainWindow._build_layout` and `MainWindow._build_widgets` MUST become
one-line shims that call the layout functions.

#### Scenario: Window still builds correctly

- **WHEN** `MainWindow.__init__` runs
- **THEN** the central widget, sidebar, tabs, status bar, and labels are all
  configured as before.

### Requirement: `_initialize_window_state` must be a factory function

The body of `MainWindow._initialize_window_state` MUST move to
`src/xfinaudio/desktop/window_factory.py` as
`initialize_window_state(window, scan_service, repository, settings,
settings_repository)`.

`MainWindow._initialize_window_state` MUST become a one-line shim that calls
the factory.

#### Scenario: Window state still initialized

- **WHEN** `MainWindow.__init__` runs
- **THEN** `_state`, `_workflow_service`, `_scan_service`, `_recommendation_service`,
  all the screens, view models, and controllers are all initialized as before.

### Requirement: Property accessors must move to `AppState`

The 15 property accessors on `MainWindow` MUST be removed. The state they
exposed MUST live directly on `AppState`. `MainWindow` MUST expose a
`__getattr__` and `__setattr__` shim that delegates attribute access on the
window to `self._state.<name>` for the names that were previously properties.

#### Scenario: All existing call sites still work

- **WHEN** any code does `main_window.selected_folder = path` or reads
  `main_window.last_recommendation`
- **THEN** the value is stored/retrieved on `self._state.selected_folder` or
  `self._state.last_recommendation` respectively, transparently to the caller.

#### Scenario: Test suite still passes

- **WHEN** `uv run pytest -q` is invoked
- **THEN** all 848 tests pass with no assertion changes.

## MODIFIED Requirements

None.

## REMOVED Requirements

None.

## Invariants

- The full test suite (848 tests) MUST continue to pass unmodified. Imports
  MAY be updated; assertions MUST NOT.
- `main_window.py` after this PR MUST be under 700 LOC (target <500).
- The 4 controllers (AppController, LibraryController, SettingsController,
  DjReadinessController) MUST NOT be modified beyond receiving new wiring.
- `AppState` MUST grow to own the 15 attributes previously exposed via
  properties, but its public attribute names MUST stay the same.
