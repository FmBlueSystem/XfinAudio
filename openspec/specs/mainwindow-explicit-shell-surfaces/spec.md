# Spec: MainWindow explicit shell compatibility surfaces

## Requirement: MainWindow avoids legacy shell compatibility facades internally

`MainWindow` MUST depend on explicit state compatibility helpers and MUST NOT depend on the legacy `desktop.shell_compat` facade or the removed layout graft surface.

### Scenario: MainWindow does not import shell compatibility facades
Given the `xfinaudio.desktop.main_window` source is inspected
When imports and compatibility call sites are checked
Then it must not import or reference `shell_compat`
And it must not import or reference `shell_layout_compat`
And it must not call `install_legacy_layout_methods`
And it must reference `shell_state_compat`

## Requirement: State compatibility facade remains compatible

Existing state-compatibility imports from `desktop.shell_compat` MUST remain valid during the migration.

### Scenario: Existing state compatibility facade exports remain stable
Given existing tests import `desktop.shell_compat`
When they access legacy state compatibility names
Then the names must continue to resolve to `shell_state_compat`.
