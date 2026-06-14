# Specs for mainwindow-slice3-cleanup

> Delta for `desktop-main-window`
> Source: `openspec/changes/mainwindow-slice3-cleanup/specs/desktop-main-window/spec.md`

## ADDED Requirements

### Requirement: MenuBuilder Encapsulation

All menu construction logic MUST reside in `MenuBuilder`, not in `MainWindow`. `MainWindow` MUST delegate menu construction via a single call to its `MenuBuilder` instance. `MainWindow` line count MUST decrease by at least 50 lines from this extraction.

#### Scenario: Menu construction delegates to MenuBuilder

- GIVEN the `mainwindow-slice3-cleanup` change is applied
- WHEN `MainWindow` source is reviewed
- THEN `_build_menu` and `_show_about_dialog` logic MUST NOT exist in `MainWindow`
- AND `MainWindow` MUST contain a single delegation call such as `self._menu_builder.build(self.menuBar())`

#### Scenario: Menu bar renders identically after extraction

- GIVEN a `MainWindow` instance constructed in an offscreen Qt environment
- WHEN the menu bar is inspected after `MenuBuilder` extraction
- THEN menu titles, actions, shortcuts, and About dialog trigger MUST match the behavior before the extraction

#### Scenario: Existing tests pass after MenuBuilder extraction

- GIVEN the full test suite is run after `MenuBuilder` is introduced
- WHEN all `MainWindow`-related tests execute
- THEN all tests MUST pass without modification

#### Scenario: MainWindow line count decreases from menu extraction

- GIVEN `MainWindow` before and after `MenuBuilder` extraction
- WHEN the total line count is compared
- THEN `MainWindow` MUST contain at least 50 fewer lines after the extraction

---

### Requirement: SettingsController Encapsulation

All settings dialog opening and application logic MUST reside in `SettingsController`, not in `MainWindow`. `MainWindow` MUST delegate settings interactions to its `SettingsController` instance.

#### Scenario: Settings logic lives in SettingsController

- GIVEN the `mainwindow-slice3-cleanup` change is applied
- WHEN `MainWindow` source is reviewed
- THEN `_open_settings_dialog` and `_apply_settings` logic MUST NOT exist in `MainWindow`
- AND `MainWindow` MUST contain only thin delegation calls to `SettingsController`

#### Scenario: Settings dialog opens correctly after extraction

- GIVEN a `MainWindow` instance constructed in an offscreen Qt environment
- WHEN the action that triggers settings is invoked via `MainWindow`
- THEN `SettingsController` MUST handle dialog construction and application of changed settings
- AND externally observable behavior MUST match the behavior before the extraction

#### Scenario: Existing tests pass after SettingsController extraction

- GIVEN the full test suite is run after `SettingsController` is introduced
- WHEN all `MainWindow`-related tests execute
- THEN all tests MUST pass without modification

---

### Requirement: ExportHost Protocol Boundary

An `ExportHost` Protocol MUST be defined exposing only the members `ExportCoordinator` actually accesses on its host. `ExportCoordinator.__init__` MUST accept `ExportHost` instead of `MainWindow`. `MainWindow` MUST satisfy `ExportHost` structurally without explicit inheritance.

#### Scenario: ExportHost Protocol is defined with minimal surface

- GIVEN the `mainwindow-slice3-cleanup` change is applied
- WHEN `ExportHost` is reviewed
- THEN it MUST declare only the attributes and methods that `ExportCoordinator` actually reads or calls on `host`
- AND it MUST NOT expose unrelated `MainWindow` members

#### Scenario: ExportCoordinator accepts ExportHost, not MainWindow

- GIVEN `ExportCoordinator.__init__` after the protocol is introduced
- WHEN its type annotation for the host parameter is inspected
- THEN the parameter MUST be typed as `ExportHost`, not `MainWindow`
- AND the `TYPE_CHECKING` import of `MainWindow` inside `export_coordinator.py` MUST be removed

#### Scenario: MainWindow satisfies ExportHost structurally

- GIVEN `MainWindow` as the concrete host passed to `ExportCoordinator`
- WHEN a static type checker validates the assignment
- THEN `MainWindow` MUST satisfy `ExportHost` through structural subtyping with no explicit `implements` or inheritance declaration required

#### Scenario: All export tests pass with ExportHost Protocol

- GIVEN the full export test suite after `ExportHost` is introduced
- WHEN all export-related tests execute
- THEN all existing export assertions MUST pass without modification

---

### Requirement: Zero Lint Errors After Cleanup

`uv run ruff check src/ tests/` MUST return 0 errors after this change. Lint fixes MUST be behaviorally inert.

#### Scenario: Ruff reports zero errors after lint fixes

- GIVEN the 7 pre-existing lint errors are fixed (`i18n.py` F401, `build_screen.py` E501, `review_screen.py` E501×2 / F841 / B905, `table_populators.py` E501×2, `track_repository.py` SIM105)
- WHEN `uv run ruff check src/ tests/` is executed
- THEN the command MUST exit with code 0 and report no errors

#### Scenario: Lint fixes introduce no behavioral changes

- GIVEN the lint fixes are applied in isolation
- WHEN the full test suite is run
- THEN all existing tests MUST pass
- AND no product workflow, output, or observable state MUST change
