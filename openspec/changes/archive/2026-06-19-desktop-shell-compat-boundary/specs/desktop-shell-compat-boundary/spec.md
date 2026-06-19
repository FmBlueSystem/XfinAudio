# desktop-shell-compat-boundary Specification

## ADDED Requirements

### Requirement: Legacy shell methods remain available

`MainWindow` MUST continue to expose the legacy layout-backed methods currently used by desktop callers while the shell cleanup is migrated in slices.

#### Scenario: MainWindow exposes selected legacy methods

- **GIVEN** the `MainWindow` class is imported
- **WHEN** callers access legacy layout-backed methods such as `choose_folder`, `_apply_song_filter`, and `_refresh_idle_action_state`
- **THEN** each method is callable on `MainWindow`

### Requirement: Compatibility grafting is explicit

The dynamic method grafting boundary MUST be named as desktop shell compatibility instead of being hidden in layout construction.

#### Scenario: layout no longer owns method installation

- **GIVEN** `xfinaudio.desktop.layout` is imported
- **WHEN** maintainers inspect its public responsibilities
- **THEN** it does not expose `install_layout_methods`

#### Scenario: shell compatibility owns method installation

- **GIVEN** `xfinaudio.desktop.shell_compat` is imported
- **WHEN** maintainers inspect `LEGACY_LAYOUT_METHODS`
- **THEN** it names the legacy methods installed on `MainWindow`

### Requirement: Product behavior is unchanged

Moving the compatibility installer MUST NOT change UI workflow behavior, business logic, audio behavior, export behavior, storage behavior, or Serato behavior.

#### Scenario: MainWindow behavior tests still pass

- **GIVEN** the compatibility boundary has moved
- **WHEN** the focused MainWindow tests run
- **THEN** they pass without changing expected UI behavior
