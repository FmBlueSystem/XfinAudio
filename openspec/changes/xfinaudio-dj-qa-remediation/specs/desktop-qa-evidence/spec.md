# Delta for Desktop QA Evidence

## ADDED Requirements

### Requirement: Automated Gates Are Fresh And Recorded

The system MUST use fresh automated gate evidence before claiming the remediation is complete.

#### Scenario: Test and lint evidence is current

- GIVEN the remediation is ready for verification
- WHEN verification runs
- THEN `uv run pytest -q`, `uv run ruff check .`, and `uv run ruff format --check .` MUST be executed in the current workspace
- AND the verify report MUST record the exact result.

#### Scenario: Release gate evidence is current

- GIVEN release-readiness claims are made
- WHEN verification runs
- THEN `uv run python scripts/release_gate_check.py --run` MUST be executed or a blocker MUST be recorded.

### Requirement: Controlled DJ Workflow Evidence

The system MUST validate the desktop flow as a DJ workflow, not only as isolated code.

#### Scenario: Controlled E2E export flow is validated

- GIVEN a complete real-library anchor track is available
- WHEN the controlled desktop flow is run
- THEN the flow MUST select the anchor, generate recommendation, review readiness, preview export, and either block export or write only to a temporary Serato target.

#### Scenario: Screenshot evidence supports visual inspection

- GIVEN UI guidance or layout changes are implemented
- WHEN verification runs
- THEN screenshots or equivalent rendered evidence SHOULD be captured for the affected screens.

#### Scenario: Manual DJ QA is required before release claims

- GIVEN all automated gates pass
- WHEN release or publication readiness is claimed
- THEN manual DJ workflow QA MUST be rerun and recorded.
