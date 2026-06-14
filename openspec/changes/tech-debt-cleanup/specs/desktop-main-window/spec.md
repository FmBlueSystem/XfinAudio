# Delta for desktop-main-window

## REMOVED Requirements

### Requirement: `_populate_prep_copilot_table` Method on MainWindow

`MainWindow._populate_prep_copilot_table` MUST NOT exist after this change.

(Reason: Dead code — `BuildScreen.render` replaced this method in the previous cycle; the method is unreachable in production and its retention is misleading.)
(Migration: None. The free function `table_populators.populate_prep_copilot_table` is unchanged and continues to be used by `BuildScreen`. No callers outside `MainWindow` reference the dead method.)

## ADDED Requirements

### Requirement: Export Coordination Delegation

All export logic (Serato crate, Rekordbox XML, Traktor NML, VirtualDJ XML) MUST reside in `ExportCoordinator`, not in `MainWindow`. `MainWindow` export-related methods MUST be thin delegation wrappers only; they MUST contain no export logic themselves.

#### Scenario: Export logic lives in ExportCoordinator

- GIVEN the `tech-debt-cleanup` change is applied
- WHEN `MainWindow` source is reviewed
- THEN `preview_export`, `export_recommendation`, Serato-specific preview/export methods, metadata worklist export, export history recording, and `_selected_export_software` MUST NOT contain export logic — they MUST delegate to `ExportCoordinator`

#### Scenario: Existing export tests pass via delegation

- GIVEN the full export test suite (`test_main_window.py` and any export-specific tests)
- WHEN run after `ExportCoordinator` extraction
- THEN all existing export assertions MUST pass without modification

#### Scenario: MainWindow line count decreases

- GIVEN `MainWindow` before and after the extraction
- WHEN the total line count is compared
- THEN `MainWindow` MUST contain at least 150 fewer lines after the extraction

#### Scenario: All four export targets remain functional

- GIVEN a valid `PlaylistRecommendation` and safe export folder are present
- WHEN each of Serato, Rekordbox, Traktor, and VirtualDJ exports is triggered via `MainWindow` delegation methods
- THEN the corresponding export coordinator logic MUST execute and produce the same result as before the extraction

### Requirement: Scan Thread Cancellation Coverage

A test MUST verify that starting a scan while one is already running cancels the previous scan before starting the new one.

#### Scenario: Second scan cancels first scan

- GIVEN a scan is in progress
- WHEN a new scan is started
- THEN the previous scan thread MUST be cancelled
- AND the new scan MUST NOT start until the previous thread has stopped

### Requirement: Search Debounce Test Coverage

A test MUST verify that rapid `textChanged` signals result in exactly one filter call after 150 ms.

#### Scenario: Rapid keystrokes produce a single filter call

- GIVEN the search field receives multiple `textChanged` signals within a 150 ms window
- WHEN the 150 ms debounce timer expires
- THEN exactly one filter call MUST have been made
- AND no filter call MUST have occurred before the timer expired
