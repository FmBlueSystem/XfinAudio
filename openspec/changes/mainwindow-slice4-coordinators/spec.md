# Specs for mainwindow-slice4-coordinators

> Delta for `desktop-main-window`
> Source: `openspec/changes/mainwindow-slice4-coordinators/specs/desktop-main-window/spec.md`

## ADDED Requirements

### Requirement: ScanCoordinator Encapsulation

All scan orchestration logic MUST reside in `ScanCoordinator`, not in `MainWindow`. A `ScanHost(Protocol)` MUST be defined exposing only the members `ScanCoordinator` actually accesses. `MainWindow` scan-related public methods MUST be 1-line delegations to `ScanCoordinator`. `MainWindow` line count MUST decrease by at least 50 lines from this extraction.

#### Scenario: Scan orchestration lives in ScanCoordinator

- GIVEN the `mainwindow-slice4-coordinators` change is applied
- WHEN `MainWindow` source is reviewed
- THEN `_begin_scan_state`, `_end_scan_state`, `_start_scan_worker`, `_finish_scan`, `_fail_scan`, `_show_scan_progress`, and `_show_scan_completion_status` logic MUST NOT exist in `MainWindow`
- AND `MainWindow.scan_selected_folder` and `MainWindow.cancel_scan` MUST each be a single delegation call to `self._scan_coordinator`

#### Scenario: ScanHost Protocol exposes minimal surface

- GIVEN the `mainwindow-slice4-coordinators` change is applied
- WHEN `ScanHost` is reviewed
- THEN it MUST declare only the attributes and methods that `ScanCoordinator` actually reads or calls on its host
- AND it MUST NOT expose unrelated `MainWindow` members

#### Scenario: ScanCoordinator accepts ScanHost, not MainWindow

- GIVEN `ScanCoordinator.__init__` after the protocol is introduced
- WHEN its type annotation for the host parameter is inspected
- THEN the parameter MUST be typed as `ScanHost`, not `MainWindow`
- AND any `TYPE_CHECKING` import of `MainWindow` inside `scan_coordinator.py` MUST be absent

#### Scenario: MainWindow satisfies ScanHost structurally

- GIVEN `MainWindow` as the concrete host passed to `ScanCoordinator`
- WHEN a static type checker validates the assignment
- THEN `MainWindow` MUST satisfy `ScanHost` through structural subtyping with no explicit inheritance declaration required

#### Scenario: All existing scan tests pass after extraction

- GIVEN the full test suite is run after `ScanCoordinator` is introduced
- WHEN all scan-related tests execute
- THEN all existing scan assertions MUST pass without modification

#### Scenario: MainWindow line count decreases from scan extraction

- GIVEN `MainWindow` before and after `ScanCoordinator` extraction
- WHEN the total line count is compared
- THEN `MainWindow` MUST contain at least 50 fewer lines after the extraction

---

### Requirement: RecommendationCoordinator Encapsulation

All recommendation orchestration logic MUST reside in `RecommendationCoordinator`, not in `MainWindow`. A `RecommendationHost(Protocol)` MUST be defined exposing only the members `RecommendationCoordinator` actually accesses. `MainWindow` recommendation-related public methods MUST be 1-line delegations to `RecommendationCoordinator`. `MainWindow` line count MUST decrease by at least 50 lines from this extraction.

#### Scenario: Recommendation orchestration lives in RecommendationCoordinator

- GIVEN the `mainwindow-slice4-coordinators` change is applied
- WHEN `MainWindow` source is reviewed
- THEN `_begin_recommendation_state`, `_end_recommendation_state`, `_start_recommendation_worker`, `_finish_recommendation`, `_fail_recommendation`, and `_on_recommend_requested` logic MUST NOT exist in `MainWindow`
- AND `MainWindow.recommend_playlist` MUST be a single delegation call to `self._recommendation_coordinator`

#### Scenario: RecommendationHost Protocol exposes minimal surface

- GIVEN the `mainwindow-slice4-coordinators` change is applied
- WHEN `RecommendationHost` is reviewed
- THEN it MUST declare only the attributes and methods that `RecommendationCoordinator` actually reads or calls on its host
- AND it MUST NOT expose unrelated `MainWindow` members

#### Scenario: RecommendationCoordinator accepts RecommendationHost, not MainWindow

- GIVEN `RecommendationCoordinator.__init__` after the protocol is introduced
- WHEN its type annotation for the host parameter is inspected
- THEN the parameter MUST be typed as `RecommendationHost`, not `MainWindow`
- AND any `TYPE_CHECKING` import of `MainWindow` inside `recommendation_coordinator.py` MUST be absent

#### Scenario: MainWindow satisfies RecommendationHost structurally

- GIVEN `MainWindow` as the concrete host passed to `RecommendationCoordinator`
- WHEN a static type checker validates the assignment
- THEN `MainWindow` MUST satisfy `RecommendationHost` through structural subtyping with no explicit inheritance declaration required

#### Scenario: All existing recommendation tests pass after extraction

- GIVEN the full test suite is run after `RecommendationCoordinator` is introduced
- WHEN all recommendation-related tests execute
- THEN all existing recommendation assertions MUST pass without modification

#### Scenario: MainWindow line count decreases from recommendation extraction

- GIVEN `MainWindow` before and after `RecommendationCoordinator` extraction
- WHEN the total line count is compared
- THEN `MainWindow` MUST contain at least 50 fewer lines after the extraction

---

### Requirement: No Product Feature or UX Change from Coordinator Extraction

This change MUST be a behavior-preserving refactor only. `MainWindow` scan and recommendation workflows MUST remain externally indistinguishable after coordinator extraction.

#### Scenario: Scan workflow is unchanged after extraction

- GIVEN a user triggers a folder scan via `MainWindow`
- WHEN `ScanCoordinator` handles the orchestration
- THEN progress labels, status labels, button enabled/disabled states, cancellation behavior, and final library state MUST match the behavior before the extraction

#### Scenario: Recommendation workflow is unchanged after extraction

- GIVEN a user triggers a playlist recommendation via `MainWindow`
- WHEN `RecommendationCoordinator` handles the orchestration
- THEN recommendation table contents, guidance labels, button states, and error feedback MUST match the behavior before the extraction

#### Scenario: Full test suite passes with zero failures after both extractions

- GIVEN both `ScanCoordinator` and `RecommendationCoordinator` are introduced
- WHEN `uv run pytest -q` is executed
- THEN the command MUST exit with zero failures
- AND `uv run ruff check .` MUST report zero errors
