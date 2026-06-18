# Spec: Collapse desktop services

## ADDED Requirements

### Requirement: Dead production modules must be removed

`src/xfinaudio/desktop/recommendation_worker.py` and
`src/xfinaudio/desktop/live_assistant_state.py` have zero production importers.
Their only references are in their own test files. Both files SHALL be deleted,
along with the corresponding test files.

#### Scenario: No dead desktop modules

- **WHEN** `git ls-files src/xfinaudio/desktop/recommendation_worker.py src/xfinaudio/desktop/live_assistant_state.py` is invoked
- **THEN** it returns no entries.
- **WHEN** `git ls-files tests/test_recommendation_worker.py tests/test_live_assistant_state.py` is invoked
- **THEN** it returns no entries.

### Requirement: ScanController and ScanCoordinator must be merged

The `ScanController` (QThread lifecycle) and `ScanCoordinator` (state machine +
Protocol-bound host access) exist as a pair with exactly one production consumer
(`MainWindow`). They SHALL be merged into a single `ScanService` class. The
`ScanHost` Protocol SHALL be removed; the service shall take its dependencies
explicitly via constructor injection.

#### Scenario: One scan service module

- **WHEN** `git ls-files src/xfinaudio/desktop/scan_controller.py src/xfinaudio/desktop/scan_coordinator.py` is invoked
- **THEN** it returns no entries.
- **WHEN** `git ls-files src/xfinaudio/desktop/scan_service.py` is invoked
- **THEN** it returns exactly one entry.

### Requirement: RecommendationController and RecommendationCoordinator must be merged

The `RecommendationController` and `RecommendationCoordinator` exist as a pair
with exactly one production consumer. They SHALL be merged into a single
`RecommendationService` class. The `RecommendationHost` Protocol SHALL be removed.

#### Scenario: One recommendation service module

- **WHEN** `git ls-files src/xfinaudio/desktop/recommendation_controller.py src/xfinaudio/desktop/recommendation_coordinator.py` is invoked
- **THEN** it returns no entries.
- **WHEN** `git ls-files src/xfinaudio/desktop/recommendation_service.py` is invoked
- **THEN** it returns exactly one entry.

### Requirement: Screen-local coordinators must be moved to their screens

`LiveAssistantCoordinator` (single caller: `MainWindow`) and
`SettingsController` (single caller: `MainWindow`) have no business existing as
separate modules. They SHALL be merged into their owning screen/dialog files:

- `LiveAssistantCoordinator` → `screens/live_assistant_screen.py`
- `SettingsController` → `settings_dialog.py`

`NavigationController` and `MenuBuilder` SHALL be renamed (drop the
`Controller`/`Builder` suffix) and stay in `src/xfinaudio/desktop/` as
`navigation.py` and `menu.py`.

#### Scenario: No thin-wrapper desktop modules

- **WHEN** `git ls-files src/xfinaudio/desktop/live_assistant_coordinator.py src/xfinaudio/desktop/settings_controller.py` is invoked
- **THEN** it returns no entries.
- **WHEN** `git ls-files src/xfinaudio/desktop/menu_builder.py src/xfinaudio/desktop/navigation_controller.py` is invoked
- **THEN** it returns no entries.
- **WHEN** `git ls-files src/xfinaudio/desktop/menu.py src/xfinaudio/desktop/navigation.py` is invoked
- **THEN** it returns exactly one entry each.

## MODIFIED Requirements

None.

## REMOVED Requirements

None.

## Invariants

- The full test suite (861 tests at the time of this change) MUST continue to pass
  unmodified. The 4 test files for the moved/merged modules MAY require import
  path updates but MUST NOT have their assertions changed.
- `main_window.py` MUST continue to compile. The set of public method names it
  calls on the moved/merged modules MAY change (e.g. `ScanCoordinator` →
  `ScanService` with the same public API surface), but the call sites MUST be
  updated in the same commit.
- `export_coordinator.py`, `export_view_model.py`, `playlist_coordinator.py`,
  `recommendation_presenter.py` MUST NOT change in this PR.
- `pyproject.toml` and the dependency graph MUST NOT change.
