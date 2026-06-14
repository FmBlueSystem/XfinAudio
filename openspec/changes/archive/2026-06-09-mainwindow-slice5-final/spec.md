# Specs for mainwindow-slice5-final

> Delta for `desktop-main-window`
> Source: `openspec/changes/mainwindow-slice5-final/specs/desktop-main-window/spec.md`

## ADDED Requirements

### Requirement: Property Alias Layer Removal

`MainWindow` MUST NOT contain any `@property` shim that re-exposes a child widget from a Screen. All alias-based widget accesses in `MainWindow` internals MUST be replaced with direct `_screen` attribute references. All 741 existing tests MUST pass after the migration. `MainWindow` line count MUST decrease by at least 200 lines from alias removal.

#### Scenario: No forwarding properties remain in MainWindow

- GIVEN the `mainwindow-slice5-final` change is applied
- WHEN `MainWindow` source is reviewed
- THEN it MUST contain zero `@property` definitions that return a child widget attribute from a nested Screen
- AND the removed shims MUST include at minimum `folder_button`, `scan_button`, `strategy_combo`, `recommendation_table`, and `prep_copilot_table`

#### Scenario: Tests access widgets through canonical screen paths

- GIVEN `tests/test_main_window.py` after alias removal
- WHEN every test assertion referencing a formerly aliased widget is reviewed
- THEN each access MUST use the form `window._<screen>.<widget>` (e.g., `window._library_screen.tracks_table`)
- AND zero references of the form `window.<alias>` MUST remain

#### Scenario: Full test suite passes after alias removal

- GIVEN all 741 tests in the suite after `@property` alias removal
- WHEN `uv run pytest -q` is executed
- THEN the command MUST exit with zero failures

#### Scenario: MainWindow line count decreases from alias removal

- GIVEN `MainWindow` before and after alias removal
- WHEN the total line count is compared
- THEN `MainWindow` MUST contain at least 200 fewer lines after the removal

---

### Requirement: PlaylistCoordinator Encapsulation

All playlist orchestration logic MUST reside in `PlaylistCoordinator`, not in `MainWindow`. A `PlaylistHost(Protocol)` MUST be defined exposing only the members `PlaylistCoordinator` actually accesses. `MainWindow` playlist-related public methods MUST be 1-line delegations to `PlaylistCoordinator`. All existing playlist tests MUST pass after extraction.

#### Scenario: Playlist orchestration lives in PlaylistCoordinator

- GIVEN the `mainwindow-slice5-final` change is applied
- WHEN `MainWindow` source is reviewed
- THEN `MyPlaylistsScreen` CRUD signal wiring, `PlaylistEditor` save/export/track-removed signal wiring, and `PlaylistRepository` calls MUST NOT exist in `MainWindow`
- AND `MainWindow` playlist-facing public methods MUST each be a single delegation call to `self._playlist_coordinator`

#### Scenario: PlaylistHost Protocol exposes minimal surface

- GIVEN the `mainwindow-slice5-final` change is applied
- WHEN `PlaylistHost` is reviewed
- THEN it MUST declare only the attributes and methods that `PlaylistCoordinator` actually reads or calls on its host
- AND it MUST NOT expose unrelated `MainWindow` members

#### Scenario: PlaylistCoordinator accepts PlaylistHost, not MainWindow

- GIVEN `PlaylistCoordinator.__init__` after the protocol is introduced
- WHEN its type annotation for the host parameter is inspected
- THEN the parameter MUST be typed as `PlaylistHost`, not `MainWindow`
- AND any `TYPE_CHECKING` import of `MainWindow` inside `playlist_coordinator.py` MUST be absent

#### Scenario: MainWindow satisfies PlaylistHost structurally

- GIVEN `MainWindow` as the concrete host passed to `PlaylistCoordinator`
- WHEN a static type checker validates the assignment
- THEN `MainWindow` MUST satisfy `PlaylistHost` through structural subtyping with no explicit inheritance declaration required

#### Scenario: All existing playlist tests pass after extraction

- GIVEN the full test suite is run after `PlaylistCoordinator` is introduced
- WHEN all playlist-related tests execute
- THEN all existing playlist assertions MUST pass without modification

---

### Requirement: LiveAssistantCoordinator Encapsulation

All live assistant orchestration logic MUST reside in `LiveAssistantCoordinator`, not in `MainWindow`. A `LiveAssistantHost(Protocol)` MUST be defined exposing only the members `LiveAssistantCoordinator` actually accesses. `MainWindow` live-assistant-related public methods MUST be 1-line delegations to `LiveAssistantCoordinator`. All existing live assistant tests MUST pass after extraction.

#### Scenario: Live assistant orchestration lives in LiveAssistantCoordinator

- GIVEN the `mainwindow-slice5-final` change is applied
- WHEN `MainWindow` source is reviewed
- THEN `LiveAssistantScreen` exit/preview/load-next signal wiring, `_on_live_load_next` candidate recalculation, and live assistant tab navigation logic MUST NOT exist in `MainWindow`
- AND `MainWindow` live-assistant-facing public methods MUST each be a single delegation call to `self._live_assistant_coordinator`

#### Scenario: LiveAssistantHost Protocol exposes minimal surface

- GIVEN the `mainwindow-slice5-final` change is applied
- WHEN `LiveAssistantHost` is reviewed
- THEN it MUST declare only the attributes and methods that `LiveAssistantCoordinator` actually reads or calls on its host
- AND it MUST NOT expose unrelated `MainWindow` members

#### Scenario: LiveAssistantCoordinator accepts LiveAssistantHost, not MainWindow

- GIVEN `LiveAssistantCoordinator.__init__` after the protocol is introduced
- WHEN its type annotation for the host parameter is inspected
- THEN the parameter MUST be typed as `LiveAssistantHost`, not `MainWindow`
- AND any `TYPE_CHECKING` import of `MainWindow` inside `live_assistant_coordinator.py` MUST be absent

#### Scenario: MainWindow satisfies LiveAssistantHost structurally

- GIVEN `MainWindow` as the concrete host passed to `LiveAssistantCoordinator`
- WHEN a static type checker validates the assignment
- THEN `MainWindow` MUST satisfy `LiveAssistantHost` through structural subtyping with no explicit inheritance declaration required

#### Scenario: All existing live assistant tests pass after extraction

- GIVEN the full test suite is run after `LiveAssistantCoordinator` is introduced
- WHEN all live-assistant-related tests execute
- THEN all existing live assistant assertions MUST pass without modification

---

### Requirement: No Product Feature or UX Change from Slice 5

This change MUST be a behavior-preserving refactor only. All `MainWindow` playlist and live assistant workflows MUST remain externally indistinguishable after coordinator extraction and alias removal.

#### Scenario: Playlist workflow is unchanged after extraction

- GIVEN a user interacts with `MyPlaylistsScreen` CRUD or `PlaylistEditor` save/export flows via `MainWindow`
- WHEN `PlaylistCoordinator` handles the orchestration
- THEN playlist list contents, editor state, save/export outcomes, and repository side effects MUST match the behavior before the extraction

#### Scenario: Live assistant workflow is unchanged after extraction

- GIVEN a user interacts with `LiveAssistantScreen` exit/preview/load-next flows via `MainWindow`
- WHEN `LiveAssistantCoordinator` handles the orchestration
- THEN suggestion recalculation results, tab navigation behavior, audio player state, and screen state MUST match the behavior before the extraction

#### Scenario: Full test suite passes with zero failures after all slice 5 changes

- GIVEN alias removal, `PlaylistCoordinator`, and `LiveAssistantCoordinator` are all introduced
- WHEN `uv run pytest -q` is executed
- THEN the command MUST exit with zero failures
- AND `uv run ruff check .` MUST report zero errors
- AND `uv run ruff format --check .` MUST pass
