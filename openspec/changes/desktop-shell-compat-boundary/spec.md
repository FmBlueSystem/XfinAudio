# Spec: Desktop shell compatibility boundary

## Requirement: legacy shell methods remain available

GIVEN a `MainWindow` class
WHEN the desktop shell module is imported
THEN the legacy layout methods required by current UI tests remain available on `MainWindow`.

## Requirement: compatibility grafting is explicit

GIVEN the legacy methods are still installed dynamically
WHEN a maintainer searches for the compatibility boundary
THEN the boundary is named as shell compatibility rather than hidden inside layout construction.

## Requirement: behavior is unchanged

GIVEN an existing desktop workflow test
WHEN the compatibility boundary moves
THEN the same focused MainWindow tests pass without UI copy, navigation, export, scan, recommendation, or AppState behavior changes.
