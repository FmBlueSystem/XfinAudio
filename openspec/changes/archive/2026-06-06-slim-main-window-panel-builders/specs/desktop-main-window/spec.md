# Delta for Desktop Main Window

## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Public Desktop Entry Point Compatibility

The system MUST preserve the public desktop application entry point and `MainWindow` compatibility contract while slimming internal rendering and construction responsibilities.
(Previously: The requirement covered entrypoint compatibility while slimming internal rendering responsibilities.)

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
(Previously: The requirement covered existing widget attributes and wrapper methods, but did not explicitly call out constructor-extracted signal behavior.)

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

### Requirement: No Product Feature or UX Change

The system MUST treat this change as a behavior-preserving refactor only and MUST NOT introduce product feature, workflow, copy, layout, or visual behavior changes while extracting constructor/page/panel builders.
(Previously: The requirement treated constructor/page builders as deferred outside the earlier table-populator slice.)

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
(Previously: The requirement covered extracted table-population behavior only.)

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
