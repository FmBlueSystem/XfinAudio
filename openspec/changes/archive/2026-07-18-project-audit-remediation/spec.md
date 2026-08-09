# Project Maintenance Quality Specification

## Purpose

Define enforceable quality gates for deterministic desktop testing, bounded dependencies, complete SDD records, and behavior-preserving decomposition.

## Requirements

### Requirement: Deterministic macOS Desktop Startup Testing

Desktop startup tests MUST isolate operating-system application activation while the normal packaged runtime MUST preserve native activation and window startup behavior.

#### Scenario: Startup test uses an isolated application service

- GIVEN desktop startup runs under an automated test
- WHEN application activation is exercised
- THEN the test MUST complete without invoking an unsafe native application singleton
- AND it MUST verify the expected activation interaction.

#### Scenario: Normal startup preserves macOS behavior

- GIVEN desktop startup runs outside the isolated test environment
- WHEN the application launches on macOS
- THEN native activation and main-window presentation MUST remain available
- AND existing startup exit semantics MUST remain unchanged.

### Requirement: Bounded and Reproducible Dependencies

Every direct runtime and development dependency MUST declare a compatible upper bound or an exact pin, and the resolved lock data MUST match those declarations.

#### Scenario: Dependency declarations are bounded

- GIVEN the project dependency declarations are inspected
- WHEN each direct dependency constraint is evaluated
- THEN every constraint MUST contain an exclusive upper bound or exact version.

#### Scenario: Lock data is synchronized

- GIVEN bounded declarations have changed
- WHEN dependencies are resolved from the project configuration
- THEN the lock data MUST satisfy every declared range
- AND standard project verification MUST use the synchronized resolution.

### Requirement: Complete Active SDD Lifecycle Records

Every active OpenSpec change MUST contain the artifacts required by project governance and MUST report a state consistent with repository evidence. Archived history MUST NOT be rewritten during reconciliation.

#### Scenario: Active change is complete and coherent

- GIVEN an OpenSpec change remains active
- WHEN its lifecycle record is audited
- THEN every required artifact MUST exist
- AND its phase status and next recommendation MUST agree with artifact evidence.

#### Scenario: Evidence is insufficient

- GIVEN an active change lacks evidence that a phase succeeded
- WHEN lifecycle state is reconciled
- THEN the phase MUST NOT be marked complete without documented evidence
- AND the record MUST expose the remaining work or blocker.

### Requirement: Behavior-Preserving Module Decomposition

Oversized desktop modules MUST be decomposed into cohesive, reviewable slices without changing public contracts, user-visible behavior, state invariants, audio safety, or export safety.

#### Scenario: Extracted responsibility preserves behavior

- GIVEN characterization coverage exists for a module responsibility
- WHEN that responsibility is extracted
- THEN existing callers and observable outcomes MUST remain compatible
- AND the focused and full verification gates MUST pass.

#### Scenario: Planned slice risks the review budget

- GIVEN a decomposition slice is forecast to exceed 400 changed lines
- WHEN delivery is planned
- THEN it MUST be split into autonomous chained slices
- AND each slice MUST define independent verification and rollback boundaries.

### Requirement: Strict TDD Remediation

Every behavior-changing remediation slice MUST follow RED, GREEN, REFACTOR, and VERIFY in order; configuration and lifecycle-only slices MUST still be verified against their applicable gates.

#### Scenario: Behavior change is implemented

- GIVEN a remediation changes observable runtime behavior
- WHEN implementation begins
- THEN a failing characterization or requirement test MUST be recorded first
- AND implementation MUST proceed only to satisfy that test before refactoring.

#### Scenario: Non-behavioral remediation is applied

- GIVEN a slice changes only configuration or lifecycle artifacts
- WHEN the slice is completed
- THEN applicable consistency and project verification gates MUST pass
- AND no unsupported product behavior change MAY be introduced.
