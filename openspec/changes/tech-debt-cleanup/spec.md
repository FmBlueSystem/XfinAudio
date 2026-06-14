# Delta Specs: tech-debt-cleanup

## Domain: desktop-main-window

### REMOVED Requirements

#### Requirement: `_populate_prep_copilot_table` Method on MainWindow

`MainWindow._populate_prep_copilot_table` MUST NOT exist after this change.

(Reason: Dead code — `BuildScreen.render` replaced this method in the previous cycle; the method is unreachable in production.)
(Migration: None. `table_populators.populate_prep_copilot_table` is unchanged and continues to serve `BuildScreen`.)

---

### ADDED Requirements

#### Requirement: Export Coordination Delegation

All export logic (Serato, Rekordbox, Traktor, VirtualDJ) MUST reside in `ExportCoordinator`. `MainWindow` export-related methods MUST be thin delegation wrappers that contain no export logic.

##### Scenario: Export logic is absent from MainWindow

- GIVEN the change is applied
- WHEN `MainWindow` source is reviewed
- THEN `preview_export`, `export_recommendation`, Serato preview/export methods, metadata worklist export, export history recording, and `_selected_export_software` MUST contain no export logic
- AND each MUST delegate to `ExportCoordinator`

##### Scenario: Existing export tests pass after extraction

- GIVEN the full export test suite
- WHEN run after the extraction
- THEN all existing assertions MUST pass without modification

##### Scenario: MainWindow shrinks by at least 150 lines

- GIVEN the pre- and post-extraction line counts of `main_window.py`
- WHEN compared
- THEN the post-extraction count MUST be at least 150 lines less than the pre-extraction count

##### Scenario: All four export targets remain functional

- GIVEN a valid `PlaylistRecommendation` and safe export folder
- WHEN each of Serato, Rekordbox, Traktor, VirtualDJ exports is invoked through `MainWindow` delegation
- THEN each export produces the same result as before the extraction

---

#### Requirement: Scan Thread Cancellation Test Coverage

A test MUST verify that starting a new scan while one is in progress cancels the previous scan before beginning the new one.

##### Scenario: Second scan cancels first scan

- GIVEN a scan thread is running
- WHEN a new scan is started
- THEN the previous scan thread MUST be cancelled
- AND the new scan MUST NOT start until the cancelled thread has fully stopped

---

#### Requirement: Search Debounce Test Coverage

A test MUST verify that rapid consecutive `textChanged` signals produce exactly one filter call after the 150 ms debounce window.

##### Scenario: Burst of keystrokes fires one filter call

- GIVEN multiple `textChanged` signals arrive within a 150 ms window
- WHEN the 150 ms timer expires
- THEN exactly one filter call MUST have been made
- AND no filter call MUST have fired before the timer expired

---

## Domain: dj-recommendation-safety

### ADDED Requirements

#### Requirement: Transition Score Cache Hit Test Coverage

A test MUST verify that `score_transition` returns a cached result on a second call with identical arguments (no recomputation), and that the `_score_cache` passed into `recommend_playlist` starts empty at the beginning of each new call.

##### Scenario: Second call with same args returns cached result

- GIVEN `score_transition` has been called once with a specific `(left, right, weights, config)` tuple in the current session
- WHEN `score_transition` is called again with the identical arguments
- THEN the return value MUST be identical to the first call's return value
- AND the underlying scoring computation MUST NOT run a second time

##### Scenario: Cache is empty at the start of each recommend_playlist call

- GIVEN `recommend_playlist` is called for a new recommendation session
- WHEN the `_score_cache` dict is inspected at the start of that call
- THEN the cache MUST be empty (no entries carried over from a prior session)

---

#### Requirement: Optimizer Exact/Heuristic Boundary Test Coverage

A test MUST verify that `recommend_sequence` with n=15 uses the exact solver path and that n=16 uses the heuristic path.

##### Scenario: n=15 uses exact solver

- GIVEN a candidate pool of exactly 15 tracks
- WHEN `recommend_sequence` is invoked
- THEN the exact TSP solver MUST be used
- AND `EXACT_LIMIT` MUST equal `15`

##### Scenario: n=16 uses heuristic solver

- GIVEN a candidate pool of exactly 16 tracks
- WHEN `recommend_sequence` is invoked
- THEN the heuristic path MUST be used
- AND the exact TSP solver MUST NOT be invoked

---

## Domain: settings-persistence

### MODIFIED Requirements

#### Requirement: `optimizer.exact_limit` Default Value

`AppSettings.optimizer.exact_limit` MUST default to `15`.
(Previously: default was `20`, which drifted from `optimizer.py`'s `EXACT_LIMIT = 15` constant.)

##### Scenario: Fresh AppSettings has exact_limit == 15

- GIVEN no persisted `settings.json` exists
- WHEN `AppSettings()` is instantiated
- THEN `AppSettings().optimizer.exact_limit` MUST equal `15`

##### Scenario: Existing settings tests pass after default change

- GIVEN the full settings test suite
- WHEN run after the default is updated to `15`
- THEN all existing tests MUST pass without modification

##### Scenario: Persisted user value is not overwritten

- GIVEN a `settings.json` that stores `optimizer.exact_limit = 20` from a prior session
- WHEN settings are loaded
- THEN the loaded value MUST be `20` (persisted value wins over factory default)
