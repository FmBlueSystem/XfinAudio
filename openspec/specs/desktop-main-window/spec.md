# Desktop Main Window Specification

## Purpose

Define the required behavior-preserving refactor constraints for the desktop `MainWindow` Qt coordinator, the extracted table-population slice, and the constructor/page/panel builder extraction slice.

## Requirements

### Requirement: Public Desktop Entry Point Compatibility

The system MUST preserve the public desktop application entry point and `MainWindow` compatibility contract while slimming internal rendering and construction responsibilities.

#### Scenario: Application entry point remains unchanged

- GIVEN the installed console entry point resolves to `xfinaudio.desktop.app:main`
- WHEN the desktop application is launched through that entry point
- THEN application startup MUST continue to construct and show the same public `MainWindow` coordinator as before the refactor.

#### Scenario: Application module remains unchanged by constructor extraction

- GIVEN the constructor/page/panel builder extraction is implemented
- WHEN desktop application startup code is reviewed or exercised
- THEN `xfinaudio.desktop.app:main` MUST remain the application entry point
- AND startup MUST NOT require a new entrypoint, factory, or panel-builder import path.

#### Scenario: MainWindow remains import-compatible

- GIVEN existing code imports and constructs `MainWindow`
- WHEN the refactored desktop UI is used
- THEN `MainWindow` MUST remain publicly available from its existing module path and construction MUST preserve the existing external contract.

### Requirement: Public Widget and Wrapper Method Compatibility

The system MUST keep existing `MainWindow` widget attributes, Qt signal behavior, and wrapper methods available with their previous externally observable behavior.

#### Scenario: Existing widget attributes remain available

- GIVEN a `MainWindow` instance is constructed in an offscreen Qt test environment
- WHEN callers access existing public widget attributes such as workflow tabs, table widgets, buttons, filters, and guidance labels
- THEN those attributes MUST exist and refer to usable Qt widgets with unchanged labels, headers, visibility expectations, enabled states, and initial content.

#### Scenario: Existing signal behavior remains available

- GIVEN a `MainWindow` instance is constructed after constructor code is split into private builders
- WHEN existing buttons, filters, table selections, header sorting, table double-clicks, and export controls are used
- THEN their externally observable signal-driven behavior MUST match the behavior before the extraction.

#### Scenario: Existing wrapper methods remain callable

- GIVEN existing callers or tests invoke `MainWindow` methods that populate library tracks or show recommendations
- WHEN those methods run after the refactor
- THEN the methods MUST remain callable on `MainWindow` and MUST produce the same externally observable table and state outcomes as before.

### Requirement: Constructor Builder Extraction Preservation

The system MUST allow `MainWindow` constructor, page, and panel construction responsibilities to be extracted into private builder methods only when the constructed desktop window remains externally indistinguishable from the pre-extraction window.

#### Scenario: Public widget attributes survive extraction

- GIVEN a `MainWindow` instance is constructed in an offscreen Qt environment
- WHEN callers access the public widget attributes that existed before the constructor extraction
- THEN each attribute MUST still exist on `MainWindow`
- AND each attribute MUST refer to a usable Qt widget of the same externally observable role as before the extraction.

#### Scenario: Signal behavior survives extraction

- GIVEN constructor-created controls, filters, tabs, and tables are available after construction
- WHEN user-observable interactions trigger the signals that were connected before the extraction
- THEN the same `MainWindow` slots, filtering behavior, sorting behavior, selection refresh behavior, and command behavior MUST remain connected and observable.

#### Scenario: Builder extraction remains private implementation detail

- GIVEN code imports or constructs `MainWindow`
- WHEN the constructor internals are refactored into builder methods
- THEN callers MUST NOT be required to import, instantiate, or depend on any new public panel-builder API.

### Requirement: Initial Desktop UI State Preservation

The system MUST preserve the initial labels, table headers, tab labels, visibility states, enabled states, guidance text, and initial content produced by `MainWindow` construction.

#### Scenario: Initial labels and headers remain unchanged

- GIVEN a `MainWindow` instance is constructed in an offscreen Qt environment
- WHEN the initial controls, guidance labels, workflow tabs, and table headers are inspected
- THEN their user-visible text, tab names, tab position, table column order, and header labels MUST match the behavior before the constructor extraction.

#### Scenario: Initial visibility and enabled states remain unchanged

- GIVEN a `MainWindow` instance is constructed before any scan, recommendation, review, export, or metadata action is performed
- WHEN buttons, action controls, review sections, export history, and recommendation/prep sections are inspected
- THEN their visible, hidden, enabled, and disabled states MUST match the behavior before the constructor extraction.

### Requirement: Library Table Population Behavior Preservation

The system MUST preserve visible and test-observable library table behavior while moving first-slice library row population responsibility out of `MainWindow` internals.

#### Scenario: Library table rows match existing behavior

- GIVEN scanned or persisted library records that were previously displayable in the library table
- WHEN the library table is populated after the refactor
- THEN row count, column order, headers, hidden path/status behavior, cell text, item sort behavior, and record-to-row lookup side effects MUST match the pre-refactor behavior.

#### Scenario: Library filtering and sorting remain stable

- GIVEN filters or table sorting are applied to the library table
- WHEN library records are repopulated by the refactored first slice
- THEN filtering results, sort order semantics, selected row behavior, and displayed cell values MUST remain unchanged.

### Requirement: Recommendation Table Population Behavior Preservation

The system MUST preserve visible and test-observable recommendation table behavior while moving first-slice recommendation row population responsibility out of `MainWindow` internals.

#### Scenario: Recommendation rows match existing behavior

- GIVEN a recommendation result that was previously renderable by `MainWindow.show_recommendation`
- WHEN the recommendation is displayed after the refactor
- THEN recommendation table row count, column order, headers, cell text, explanations, row mappings, and selected/recommended state outcomes MUST match the pre-refactor behavior.

#### Scenario: Recommendation controls remain stable

- GIVEN recommendation display updates enable, disable, or update related controls
- WHEN recommendation data is rendered after the refactor
- THEN button states, guidance text, and follow-on workflow availability MUST remain unchanged.

### Requirement: No Product Feature or UX Change

The system MUST treat this change as a behavior-preserving refactor only and MUST NOT introduce product feature, workflow, copy, layout, or visual behavior changes while extracting constructor/page/panel builders.

#### Scenario: Existing desktop flows are unchanged

- GIVEN a user performs existing scan, filter, recommendation, review, export, or metadata workflows
- WHEN the constructor-builder refactor is present
- THEN the user-visible workflow, labels, table contents, guidance strings, and outcomes MUST remain unchanged.

#### Scenario: Deferred refactor areas remain behaviorally intact

- GIVEN broad state migration, worker coordination, export behavior, scanning behavior, table-populator behavior, and unrelated display rendering are outside this constructor-builder slice
- WHEN the constructor-builder refactor is implemented
- THEN those areas MUST NOT receive product behavior changes as part of this change.

#### Scenario: Visual and layout behavior remains unchanged

- GIVEN the constructor extraction assembles the same desktop pages and panels through private methods
- WHEN the initial window is constructed
- THEN visual styling, compact layout side effects, page order, tab position, widget visibility, and user-facing layout behavior MUST match the behavior before the extraction.

### Requirement: Offscreen Qt Characterization Coverage

The system MUST validate extracted table-population and constructor-builder behavior with automated Qt tests that run offscreen and do not depend on real display rendering.

#### Scenario: Library table behavior is covered offscreen

- GIVEN the test suite runs in an offscreen Qt environment
- WHEN library table population behavior is exercised
- THEN tests MUST verify the preserved table contents, row mappings, filtering or sorting behavior, and public `MainWindow` wrapper behavior without requiring a real display.

#### Scenario: Recommendation table behavior is covered offscreen

- GIVEN the test suite runs in an offscreen Qt environment
- WHEN recommendation display behavior is exercised
- THEN tests MUST verify preserved recommendation table contents, related state, and controls without requiring a real display.

#### Scenario: Constructor behavior is covered offscreen

- GIVEN the test suite runs in an offscreen Qt environment
- WHEN a `MainWindow` instance is constructed for characterization coverage
- THEN tests MUST verify preserved public widget attributes, initial labels, table headers, tab contract, visibility states, enabled states, and construction-time signal behavior without requiring a real display.

### Requirement: Private Widget Builder Extraction

The system MUST extract the `MainWindow` constructor's widget creation and intrinsic widget configuration into a private `_build_widgets()` builder while preserving the existing public desktop window contract.

#### Scenario: Public widget attributes remain available after widget-builder extraction

- GIVEN a `MainWindow` instance is constructed in an offscreen Qt environment after widget-builder extraction
- WHEN callers access the public widget attributes that existed before the extraction
- THEN each attribute MUST still exist on `MainWindow`
- AND each attribute MUST refer to a usable Qt widget with the same externally observable role as before the extraction.

#### Scenario: Initial widget intrinsic configuration remains unchanged

- GIVEN a `MainWindow` instance is constructed after widget-builder extraction
- WHEN the window title, public widget attributes, labels, table headers, table selection behavior and mode, initial enabled and visible states, label word-wrap, and label size constraints are inspected
- THEN each inspected value MUST match the behavior before the extraction.

#### Scenario: Widget builder remains a private implementation detail

- GIVEN existing callers import or construct `MainWindow`
- WHEN widget creation is moved into `_build_widgets()`
- THEN callers MUST NOT be required to import, instantiate, or depend on any new public widget-builder or panel-builder API.

### Requirement: Constructor Orchestration Safety

The system MUST preserve a safe `MainWindow` construction order so every extracted step observes the state and widgets it depends on.

#### Scenario: Constructor steps run in dependency-safe order

- GIVEN `MainWindow` construction runs after widget-builder extraction
- WHEN the constructor orchestrates setup
- THEN it MUST initialize constructor state before building widgets
- AND it MUST build widgets before connecting widget signals
- AND it MUST connect widget signals before applying visual design
- AND it MUST apply visual design before applying the compact layout
- AND it MUST apply the compact layout before installing the central widget.

#### Scenario: Signal and visual-design setup observe built widgets

- GIVEN `_connect_widget_signals()` and visual design setup run during construction
- WHEN those steps access widget attributes
- THEN every widget attribute they depend on MUST already exist
- AND signal-driven behavior MUST remain externally observable as before the extraction.

### Requirement: PR2 Boundary Preservation

The system MUST keep this PR2 slice limited to widget creation and intrinsic widget configuration extraction, without layout/page extraction or product behavior changes.

#### Scenario: Layout and page assembly remain in the constructor slice

- GIVEN the widget-builder extraction is implemented for PR2
- WHEN the change is reviewed
- THEN central widget assembly, page layout assembly, workflow tab layout assembly, and page-builder extraction MUST NOT be introduced in this slice.

#### Scenario: Product and UX behavior remain unchanged

- GIVEN a user performs existing scan, filter, recommendation, review, export, or metadata workflows after PR2
- WHEN those workflows are observed
- THEN user-visible labels, copy, layout, visual styling, workflow order, table contents, enabled states, visibility states, and outcomes MUST match the behavior before the extraction.

### Requirement: Offscreen Widget Builder Characterization Coverage

The system MUST validate the widget-builder extraction with automated Qt characterization coverage that runs offscreen and does not depend on real display rendering.

#### Scenario: Widget builder contract is covered offscreen

- GIVEN the test suite runs in an offscreen Qt environment
- WHEN `MainWindow` construction is exercised after widget-builder extraction
- THEN tests MUST verify preserved public widget attributes, initial widget intrinsic configuration, labels, table headers, visibility states, enabled states, and tab contract without requiring a real display.

#### Scenario: Table selection configuration is covered offscreen

- GIVEN the test suite runs in an offscreen Qt environment
- WHEN `tracks_table` and `prep_copilot_table` are inspected after construction
- THEN tests MUST verify their selection behavior and selection mode match the behavior before widget-builder extraction.

---

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

### Requirement: Scan Context Reset Boundary

The system MUST clear scan-dependent recommendation state through a pure AppState transition while preserving the desktop UI's visible clearing behavior.

#### Scenario: Scan-dependent state reset is immutable

- GIVEN scan records and recommendation-derived state exist in AppState
- WHEN scan-dependent state is cleared
- THEN the reset policy MUST return a new AppState instance
- AND scanned records, records-by-path, recommendation result, explanation, quality report, readiness report, Prep Copilot plan, applied variant, and removed playlist paths MUST be cleared
- AND unrelated track constraints MUST remain unchanged.

#### Scenario: Desktop clear flow delegates state policy

- GIVEN the desktop controller clears scan-dependent state
- WHEN the reset runs
- THEN desktop code MUST delegate AppState reset policy to the pure transition helper
- AND desktop code MUST remain responsible for clearing widgets, guidance text, and rendered review/export UI only.

### Requirement: Playlist Removal State Boundary

The system MUST update playlist removal/restoration state through pure AppState transitions while preserving desktop undo and redo behavior.

#### Scenario: Playlist track removal is immutable

- GIVEN removed playlist paths already exist in AppState
- WHEN a playlist track is removed
- THEN the reset policy MUST return a new AppState instance
- AND the removed path MUST be present
- AND previously removed paths MUST remain present
- AND the original AppState MUST remain unchanged.

#### Scenario: Playlist track restoration is immutable

- GIVEN a playlist track is present in removed playlist paths
- WHEN the playlist track is restored
- THEN the reset policy MUST return a new AppState instance
- AND the restored path MUST be absent
- AND unrelated removed paths MUST remain present
- AND the original AppState MUST remain unchanged.

#### Scenario: Desktop undo orchestration remains in the controller

- GIVEN a user removes or restores a review playlist track from the desktop UI
- WHEN undo or redo is invoked
- THEN the desktop controller MUST keep command and synchronization orchestration
- AND AppState mutation policy MUST remain delegated to pure transition helpers.

### Requirement: Prep Copilot Variant State Boundary

The system MUST apply selected Prep Copilot variant state through a pure AppState transition while preserving desktop rendering, labels, and export guidance behavior.

#### Scenario: Prep Copilot variant application is immutable

- GIVEN stale recommendation state and removed playlist paths exist in AppState
- WHEN a selected Prep Copilot variant is applied
- THEN the transition MUST return a new AppState instance
- AND recommendation, explanation, quality report, readiness report, and applied variant name MUST reflect the selected variant
- AND removed playlist paths MUST be cleared
- AND the original AppState MUST remain unchanged.

#### Scenario: Desktop keeps rendering responsibility

- GIVEN a selected Prep Copilot variant is applied from the desktop UI
- WHEN the variant is rendered in review/export screens
- THEN desktop code MUST keep selection validation, labels, status messages, and table rendering responsibilities
- AND AppState mutation policy MUST remain delegated to the pure transition helper.

### Requirement: Track Constraint State Boundary

The system MUST update excluded and locked track constraints through pure AppState transitions while preserving desktop selection and synchronization behavior.

#### Scenario: Excluding selected tracks is immutable

- GIVEN excluded track paths already exist in AppState
- WHEN selected tracks are excluded
- THEN the transition MUST return a new AppState instance
- AND selected paths MUST be present in excluded paths
- AND previously excluded paths MUST remain present
- AND the original AppState MUST remain unchanged.

#### Scenario: Locking selected tracks is immutable

- GIVEN locked track paths already exist in AppState
- WHEN selected tracks are locked
- THEN the transition MUST return a new AppState instance
- AND selected paths MUST be present in locked paths
- AND previously locked paths MUST remain present
- AND the original AppState MUST remain unchanged.

#### Scenario: Clearing track constraints is immutable

- GIVEN excluded and locked track paths exist in AppState
- WHEN constraints are cleared
- THEN the transition MUST return a new AppState instance
- AND excluded and locked paths MUST be empty
- AND the original AppState MUST remain unchanged.
