# Proposal: Release Readiness Smoke Gate

## Intent

Promote the existing `scripts/smoke_release_readiness.py` from a standalone helper to a first-class automated release gate. Strengthen it with a DJ readiness check and document the runbook so the release smoke is reproducible on a clean checkout.

## Scope

### In Scope

- Harden `scripts/smoke_release_readiness.py` with a DJ readiness report.
- Add a `release readiness smoke` gate to `scripts/release_gate_check.py`.
- Update `tests/test_release_gate_check.py` to expect the new gate.
- Update `tests/test_release_smoke.py` to assert the new pass line.
- Create `docs/release-readiness-smoke.md` runbook.
- Produce SDD/TDD artifacts under `openspec/changes/release-readiness-smoke-gate/`.

### Out of Scope

- Changing product behavior or UI.
- Scanning real audio files.
- Writing to live Serato libraries.
- Packaging/build changes beyond gate wiring.

## Capabilities

- `release-readiness-smoke-gate`: Deterministic, audio-free release smoke wired into the gate runner.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `scripts/smoke_release_readiness.py` | Modified | Adds DJ readiness step. |
| `scripts/release_gate_check.py` | Modified | Registers smoke as a command gate. |
| `tests/test_release_gate_check.py` | Modified | Expects new gate in reports. |
| `tests/test_release_smoke.py` | Modified | Asserts DJ readiness pass line. |
| `docs/release-readiness-smoke.md` | Created | Runbook and expected output. |
| `openspec/changes/release-readiness-smoke-gate/` | Created | SDD/TDD artifacts. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Smoke becomes flaky on CI | Low | Deterministic fixtures only; no audio or filesystem side effects. |
| DJ readiness check mutates real files | Very low | Build a dry-run Serato plan against a temp `_Serato_` root. |

## Success Criteria

- [ ] `scripts/smoke_release_readiness.py` prints a DJ readiness pass line.
- [ ] `uv run python scripts/smoke_release_readiness.py` exits 0.
- [ ] `scripts/release_gate_check.py --run` passes the smoke gate.
- [ ] `tests/test_release_gate_check.py` passes.
- [ ] `tests/test_release_smoke.py` passes.
- [ ] All verification commands pass.
