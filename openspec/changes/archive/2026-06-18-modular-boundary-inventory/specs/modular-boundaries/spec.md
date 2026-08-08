# Modular Boundaries Capability Spec

## Functional Inventory

### Requirement: Maintainer-readable functionality map

The system SHALL provide a documentation artifact that groups XfinAudio features into independent modules and identifies the intended boundary between business logic and UI logic.

#### Scenario: Review module ownership

- GIVEN a maintainer is planning a refactor
- WHEN they read the functional inventory
- THEN each major feature lists current files, business responsibility, UI responsibility, target owner, dependencies, tests, and first extraction slice.

## Recommendation Policy Boundary

### Requirement: Candidate-pool policy lives outside desktop

The recommendation candidate-pool policy SHALL be available from `xfinaudio.recommendation` so non-UI tests and future services can use it without importing desktop widgets.

#### Scenario: Desktop asks for candidates

- GIVEN scanned tracks and optional DJ controls
- WHEN desktop needs a recommendation candidate pool
- THEN it calls a non-UI recommendation policy function.

## Strategy Selection Boundary

### Requirement: Display labels resolve to internal strategy names

The strategy registry SHALL resolve built-in display labels to their internal strategy names so UI labels do not leak into engine lookup failures.

#### Scenario: Prep Copilot receives a display label

- GIVEN the UI displays `Harmonic Journey`
- WHEN Prep Copilot builds a DJ set intent from that value
- THEN the recommendation engine receives `harmonic_journey`.
