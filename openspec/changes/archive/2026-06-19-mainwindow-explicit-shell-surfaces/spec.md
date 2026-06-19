# Spec: MainWindow explicit shell compatibility surfaces

## Requirement: MainWindow uses explicit compatibility surfaces internally

`MainWindow` MUST depend on the explicit shell compatibility modules rather than the legacy `desktop.shell_compat` facade.

### Scenario: MainWindow does not import the facade
Given the `xfinaudio.desktop.main_window` source is inspected
When imports and compatibility call sites are checked
Then it must not import or reference `shell_compat`
And it must reference `shell_layout_compat`
And it must reference `shell_state_compat`

## Requirement: Legacy facade remains compatible

Existing imports from `desktop.shell_compat` MUST remain valid during the migration.

### Scenario: Existing compatibility facade exports remain stable
Given existing tests import `desktop.shell_compat`
When they access legacy layout and state compatibility names
Then the names must continue to resolve to the explicit modules
