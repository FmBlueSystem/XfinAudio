# Proposal: Performance Baseline

## Intent

Establish deterministic, audio-free performance baselines for core user workflows so future changes can detect severe regressions in recommendation, export, quality reporting, and DJ readiness.

## Scope

### In Scope

- Create deterministic `TrackRecord` fixture generator for performance tests.
- Add `tests/test_performance_baseline.py` with time-bounded scenarios.
- Add `scripts/performance_baseline.py` reporter script that prints a Markdown table.
- Choose generous thresholds calibrated on current CI hardware.
- Produce SDD/TDD artifacts.

### Out of Scope

- Benchmarking real audio scanning.
- New product features or UI changes.
- Continuous benchmarking infrastructure.
- Translation updates.

## Capabilities

- `performance-baseline`: Automated, deterministic performance smoke tests for core workflows.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `tests/fixtures/performance_tracks.py` | Created | Deterministic track generator. |
| `tests/test_performance_baseline.py` | Created | Time-bounded baseline tests. |
| `scripts/performance_baseline.py` | Created | Markdown reporter script. |
| `openspec/changes/performance-baseline/` | Created | SDD/TDD artifacts. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Flaky timing on CI | Low | Generous thresholds, no file I/O, deterministic fixtures. |
| Slow tests | Low | Single iteration per scenario. |

## Success Criteria

- [ ] Baseline tests exist and pass.
- [ ] Reporter script prints a Markdown table.
- [ ] All verification commands pass.
