# Proposal: XfinAudio Quality Tooling Baseline

## Intent

Close the three remaining quality-gaps identified after the desktop/QA remediation: missing static type checking, missing test coverage measurement, and missing automated end-to-end smoke validation against real audio. These gaps are currently recorded as `available: false` in `openspec/config.yaml` and force the `real Mixed In Key audio QA` gate to remain manual.

This change adds the tooling and the first real-audio smoke test without changing product behavior, without mutating real DJ libraries, and without adding audio DSP or AI generation.

## Scope

### In Scope

1. Add `pyright` as the static type checker.
2. Add `pytest-cov` as the coverage runner and establish a baseline threshold.
3. Add a controlled E2E smoke test that exercises scan → persist → recommend → Serato export using a real audio fixture tagged with Mixed In Key-style metadata.
4. Update `openspec/config.yaml`, CI workflow, and SDD skill verification commands to include the new gates.

### Out of Scope

- Refactoring large modules (`main_window.py`, `export_coordinator.py`, etc.).
- New product features (waveform, cue points, preview improvements, etc.).
- Release builds, tags, DMG, notarization.
- Mutation of real Serato libraries or real audio files.

## Capabilities

### New Capabilities

- `type-checker`: Static type checking via pyright in CI and local verification.
- `test-coverage`: pytest-cov reporting with a fail-under threshold.
- `e2e-smoke-real-audio`: Automated smoke test that validates the core workflow end-to-end against a real audio fixture with MIK-style tags.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `pyproject.toml` | Modified | Add dev dependencies and tool configuration. |
| `uv.lock` | Modified | Lock new dependencies. |
| `openspec/config.yaml` | Modified | Enable type checker, coverage, and e2e smoke. |
| `.github/workflows/non-audio-release-gates.yml` | Modified | Run pyright and coverage in CI. |
| `tests/test_smoke_real_audio_scan_recommend_export.py` | Created | Real-audio E2E smoke test. |
| `tests/conftest.py` | Modified | Helper fixtures if required. |
| `.kimi/skills/gentle-ai-sdd-tdd/SKILL.md` | Modified | Verification commands. |
| `AGENTS.md` | Modified | Verification commands. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| pyright reports many existing errors | High | Start with permissive settings; fix only critical/blocking errors; suppress noisy rules. |
| Coverage threshold is too aggressive | Medium | Set initial threshold at 70% or report-only; raise later. |
| Real-audio smoke test is flaky | Low | Use deterministic temporary directories and a committed fixture; no external services. |
| CI runtime increases | Low | Run type check and coverage in the same job; keep threshold reasonable. |

## Rollback Plan

Each improvement is independently revertible:

1. Remove pyright dependency and configuration.
2. Remove pytest-cov dependency and configuration.
3. Delete the smoke test file.
4. Revert `openspec/config.yaml` and CI workflow changes.

## Dependencies

- Existing PySide6 desktop workflow remains untouched.
- Existing SQLite-backed track repository provides persistence.
- Existing Serato crate writer provides deterministic export validation.

## Success Criteria

- [ ] `uv run pytest -q` passes.
- [ ] `uv run pytest --cov --cov-fail-under=70` passes.
- [ ] `uv run pyright src tests` passes or only has justified suppressions.
- [ ] `uv run ruff check .` passes.
- [ ] `uv run ruff format --check .` passes.
- [ ] `uv run python scripts/release_gate_check.py --run` passes.
- [ ] `openspec/config.yaml` records type_checker, coverage, and e2e as available.
- [ ] CI runs pyright and coverage on every PR/push.
