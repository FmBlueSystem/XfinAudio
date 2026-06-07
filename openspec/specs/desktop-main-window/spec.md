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
