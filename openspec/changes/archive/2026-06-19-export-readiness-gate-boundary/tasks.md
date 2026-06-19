# Tasks: Export Readiness Gate Boundary

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 260-380 |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | Single PR: pure gate boundary plus desktop consumption |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Extract export readiness gate and consume it from desktop | Single PR | Keep under 400 changed lines; stop if coordinator characterization grows unexpectedly. |

## Phase 1: RED - Pure Gate Tests

- [x] 1.1 Create `tests/test_export_readiness.py` with failing unit tests for missing recommendation and blocked readiness on export only.
- [x] 1.2 Add failing tests proving non-Serato preview/export requires a safe folder, while Serato does not.
- [x] 1.3 Add a failing test proving unknown non-Serato software is allowed past readiness when recommendation and safe folder exist.

## Phase 2: GREEN - Pure Export Boundary

- [x] 2.1 Create `src/xfinaudio/exporting/export_readiness.py` with frozen request and decision models, no desktop or PySide imports.
- [x] 2.2 Implement pure `evaluate_export_gate` with preserved ordering: recommendation, export-only readiness, non-Serato safe folder, allowed.
- [x] 2.3 Keep unknown software out of readiness validation so existing planner/writer ownership remains unchanged.

## Phase 3: REFACTOR - Desktop Consumption

- [x] 3.1 Modify `src/xfinaudio/desktop/export_coordinator.py` to build gate requests and consume decision codes before planning.
- [x] 3.2 Map denied decision codes to the existing UI/status copy exactly; do not change dialog flow, planner calls, writers, or Serato behavior.
- [x] 3.3 Add/adjust `tests/test_export_coordinator.py` characterization tests for short-circuit behavior and unchanged status messages.

## Phase 4: VERIFY/Handoff Artifacts

- [x] 4.1 During apply, create `openspec/changes/export-readiness-gate-boundary/apply-progress.md` and mark completed tasks.
- [x] 4.2 Update `openspec/changes/export-readiness-gate-boundary/state.yaml` after apply, then run the later verify phase with focused tests first.
