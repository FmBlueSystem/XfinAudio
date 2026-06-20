# desktop-shell-compat-boundary Specification

## ADDED Requirements

### Requirement: Former legacy shell methods remain available explicitly

`MainWindow` MUST continue to expose the former legacy layout-backed method names currently used by desktop callers. These methods are explicit `MainWindow` methods, not dynamic layout grafts.

#### Scenario: MainWindow exposes selected former legacy methods

- **GIVEN** the `MainWindow` class is imported
- **WHEN** callers access former legacy layout-backed methods such as `choose_folder`, `_apply_song_filter`, and `_refresh_idle_action_state`
- **THEN** each method is callable on `MainWindow`

### Requirement: Layout owns no method installation

Dynamic layout method grafting MUST NOT be hidden in layout construction or shell compatibility.

#### Scenario: layout no longer owns method installation

- **GIVEN** `xfinaudio.desktop.layout` is imported
- **WHEN** maintainers inspect its public responsibilities
- **THEN** it does not expose `install_layout_methods`

#### Scenario: shell compatibility no longer owns layout grafting

- **GIVEN** `xfinaudio.desktop.shell_compat` is imported
- **WHEN** maintainers inspect its exported responsibilities
- **THEN** it exposes state compatibility only and does not expose a layout method graft map or installer.

### Requirement: Product behavior is unchanged

Removing the compatibility installer MUST NOT change UI workflow behavior, business logic, audio behavior, export behavior, storage behavior, or Serato behavior.

#### Scenario: MainWindow behavior tests still pass

- **GIVEN** the compatibility boundary has been removed
- **WHEN** the focused MainWindow tests run
- **THEN** they pass without changing expected UI behavior
