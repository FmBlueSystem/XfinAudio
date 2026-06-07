# Delta for Desktop Main Window

## ADDED Requirements

### Requirement: Public Table Aliases Refer To Visible Widgets

The system MUST ensure public `MainWindow` table attributes used by tests and automation refer to the same widgets visible to the user, or expose an explicitly named visible-widget accessor.

#### Scenario: Tracks table alias matches visible library screen table

- GIVEN a `MainWindow` instance is constructed in an offscreen Qt test environment
- WHEN callers access `window.tracks_table`
- THEN it MUST refer to the same table widget as `window._library_screen.tracks_table`
- OR the public API MUST provide a clearly named visible-library-table accessor that tests use instead.

#### Scenario: E2E automation does not inspect stale legacy widgets

- GIVEN E2E automation verifies library scan results
- WHEN it checks populated library table rows
- THEN it MUST inspect the visible library screen table
- AND it MUST NOT pass by inspecting a detached legacy table.

#### Scenario: Backward compatibility remains intentional

- GIVEN older tests or callers use existing public widget attributes
- WHEN table alias cleanup is implemented
- THEN existing compatibility MUST be preserved unless a replacement accessor is explicitly documented and tested.
