# Proposal: Project Audit Remediation

## Intent

Restore trustworthy development gates after the audit found a native macOS startup-test abort, unbounded dependencies, incomplete OpenSpec lifecycle records, and oversized modules that increase review risk.

## Proposal Question Round

Interactive questions were skipped because the user authorized fixing all findings. Assumptions: preserve product behavior; repair active lifecycle records without rewriting archived history; decompose modules through behavior-preserving slices; deliver through a feature-branch chain when the 400-line budget is at risk.

## Scope

### In Scope
- Isolate native `NSApplication` interaction so desktop startup tests are deterministic and non-aborting.
- Add upper bounds to every currently unbounded dependency and refresh `uv.lock`.
- Complete or reconcile required artifacts/state for stale active OpenSpec changes.
- Decompose `library_screen.py`, `layout.py`, and `export_coordinator.py` into reviewable, behavior-preserving slices.

### Out of Scope
- New product behavior, UI/UX changes, audio mutation, DSP, or live Serato V2 writes.
- Rewriting archived OpenSpec audit history or upgrading dependencies beyond compatible bounds.

## Capabilities

### New Capabilities
- `project-maintenance-quality`: deterministic desktop test isolation, bounded dependency policy, OpenSpec lifecycle completeness, and review-budget-aware decomposition.

### Modified Capabilities
- None; product requirements remain unchanged.

## Approach

Use strict RED → GREEN → REFACTOR → VERIFY. First characterize startup isolation, then bound/lock dependencies, reconcile lifecycle artifacts from repository evidence, and extract cohesive private collaborators while preserving public APIs. Auto-chain autonomous slices using the feature-branch-chain strategy.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `tests/`, `src/xfinaudio/desktop/app.py` | Modified | Safe macOS startup isolation |
| `pyproject.toml`, `uv.lock` | Modified | Compatible upper bounds |
| `openspec/changes/` | Modified | Lifecycle reconciliation |
| `src/xfinaudio/desktop/{screens/library_screen.py,layout.py,export_coordinator.py}` | Modified | Behavior-preserving decomposition |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Native behavior differs from test doubles | Medium | Keep production path and add focused tests |
| Refactor regression or oversized review | High | Characterization tests and chained PR slices |
| Incorrect lifecycle reconstruction | Medium | Derive status from artifacts and verification evidence |

## Rollback Plan

Revert each chain slice independently; restore prior lockfile and module boundaries without changing persisted user data.

## Dependencies

- Repaired Git metadata; existing `uv`, pytest, Pyright, Ruff, and release gate.

## Success Criteria

- [ ] Startup tests and the full verification sequence pass without native aborts.
- [ ] All declared dependencies have compatible upper bounds and a synchronized lockfile.
- [ ] Active OpenSpec changes satisfy required artifact/state rules.
- [ ] Target modules are decomposed in independently reviewable, behavior-preserving slices.
