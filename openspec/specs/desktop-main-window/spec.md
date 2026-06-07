# Desktop Main Window Specification

## Purpose

Define the required behavior-preserving refactor constraints for the desktop `MainWindow` Qt coordinator and the first extracted table-population slice.

## Requirements

### Requirement: Public Desktop Entry Point Compatibility

The system MUST preserve the public desktop application entry point and `MainWindow` compatibility contract while slimming internal rendering responsibilities.

#### Scenario: Application entry point remains unchanged

- GIVEN the installed console entry point resolves to `xfinaudio.desktop.app:main`
- WHEN the desktop application is launched through that entry point
- THEN application startup MUST continue to construct and show the same public `MainWindow` coordinator as before the refactor.

#### Scenario: MainWindow remains import-compatible

- GIVEN existing code imports and constructs `MainWindow`
- WHEN the refactored desktop UI is used
- THEN `MainWindow` MUST remain publicly available from its existing module path and construction MUST preserve the existing external contract.

### Requirement: Public Widget and Wrapper Method Compatibility

The system MUST keep existing `MainWindow` widget attributes and wrapper methods available with their previous externally observable behavior.

#### Scenario: Existing widget attributes remain available

- GIVEN a `MainWindow` instance is constructed in an offscreen Qt test environment
- WHEN callers access existing public widget attributes such as workflow tabs, table widgets, buttons, filters, and guidance labels
- THEN those attributes MUST exist and refer to usable Qt widgets with unchanged labels, headers, visibility expectations, enabled states, and initial content.

#### Scenario: Existing wrapper methods remain callable

- GIVEN existing callers or tests invoke `MainWindow` methods that populate library tracks or show recommendations
- WHEN those methods run after the refactor
- THEN the methods MUST remain callable on `MainWindow` and MUST produce the same externally observable table and state outcomes as before.

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

The system MUST treat this change as a behavior-preserving refactor only and MUST NOT introduce product feature, workflow, copy, layout, or visual behavior changes.

#### Scenario: Existing desktop flows are unchanged

- GIVEN a user performs existing scan, filter, recommendation, review, export, or metadata workflows
- WHEN the first-slice refactor is present
- THEN the user-visible workflow, labels, table contents, guidance strings, and outcomes MUST remain unchanged.

#### Scenario: Deferred refactor areas remain behaviorally intact

- GIVEN constructor/page builders, broad state migration, worker coordination, export behavior, scanning behavior, and later display populators are outside the first slice
- WHEN the first-slice refactor is implemented
- THEN those areas MUST NOT receive product behavior changes as part of this change.

### Requirement: Offscreen Qt Characterization Coverage

The system MUST validate the extracted table-population behavior with automated Qt tests that run offscreen and do not depend on real display rendering.

#### Scenario: Library table behavior is covered offscreen

- GIVEN the test suite runs in an offscreen Qt environment
- WHEN library table population behavior is exercised
- THEN tests MUST verify the preserved table contents, row mappings, filtering or sorting behavior, and public `MainWindow` wrapper behavior without requiring a real display.

#### Scenario: Recommendation table behavior is covered offscreen

- GIVEN the test suite runs in an offscreen Qt environment
- WHEN recommendation display behavior is exercised
- THEN tests MUST verify preserved recommendation table contents, related state, and controls without requiring a real display.
