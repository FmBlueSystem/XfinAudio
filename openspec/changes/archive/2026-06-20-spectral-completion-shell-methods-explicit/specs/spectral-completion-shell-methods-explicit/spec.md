# Spec: Spectral completion shell methods explicit

## Requirement: Explicit spectral completion bridge methods

Given the desktop shell uses spectral completion worker lifecycle callbacks,
When the shell compatibility layer is loaded,
Then the five spectral completion methods SHALL exist directly on `MainWindow` and SHALL NOT be dynamically installed from `LEGACY_LAYOUT_METHODS`.

## Requirement: Behavior preservation

Given spectral completion is started, cancelled, progressed, receives a profile, or finishes,
When the corresponding `MainWindow` method is invoked,
Then `LibraryController` SHALL handle the operation with existing behavior preserved.
