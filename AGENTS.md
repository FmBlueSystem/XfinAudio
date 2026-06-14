# XfinAudio Agent Governance — gentle-ai SDD/TDD

> This `AGENTS.md` governs the entire `/Users/freddymolina/Documents/audio` tree.
> It takes precedence over the global `AGENTS.md` for this project.

## Project identity

**XfinAudio** is a GPL-3.0-only, metadata-driven DJ playlist assistant for macOS.
Maintainer: **Freddy Molina** — [BlueSystem.io](https://bluesystem.io) Audio Division.

## Methodology

This repository follows **gentle-ai SDD/TDD**:

- **SDD** (Spec-Driven Development): every non-trivial change produces durable artifacts under `openspec/`.
- **TDD** (Test-Driven Development): every behavior-changing task follows RED → GREEN → REFACTOR → VERIFY.
- **gentle-ai**: changes are executed incrementally through explicit phase gates, not as monolithic patches.

When working on behavior changes, features, refactors, or bug fixes, use the project skill:

- **Skill**: `gentle-ai-sdd-tdd` — `.atl/skills/gentle-ai-sdd-tdd/SKILL.md`

## Non-negotiables

| Rule | Why |
|------|-----|
| Strict TDD | Write or update the failing test before production code. |
| No audio mutation | XfinAudio is a decision-support tool, not an editor. |
| No DSP scope | No BPM/key detection, waveform analysis, beat tracking, cue/phrase detection, rendering, mixing, time-stretching, pitch-shifting. |
| No live Serato DB V2 writes | Crate exports stay behind the safe export/backup/validation flow. |
| 400-line review budget | Exceeding it requires an explicit chained-PR plan. |
| Immutable `AppState` | Use `state.model_copy(update=...)`; never mutate in place. |
| Pinned dependencies | Use `>=lower,<upper` in `pyproject.toml` and update `uv.lock`. |

## SDD artifact locations

- `openspec/config.yaml` — project SDD configuration.
- `openspec/changes/<change-name>/` — active and historical changes.
- `openspec/specs/<capability>/spec.md` — durable capability specifications.

Every active change must contain:

```text
proposal.md
spec.md
design.md
tasks.md
apply-progress.md
verify-report.md
state.yaml   # schema: gentle-ai.sdd-state.v1
```

## Verification before finishing

Run these commands in order and ensure they pass:

```bash
uv run pytest -q
uv run pyright src tests
uv run pytest --cov --cov-fail-under=70 -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/release_gate_check.py --run
```

For focused work, run the smallest relevant `pytest` target first, then the full suite.

## Agent checklist

- [ ] I understand the change as a gentle-ai SDD/TDD change.
- [ ] I created or updated the required `openspec/` artifacts.
- [ ] I wrote or updated a failing test before production code (strict TDD).
- [ ] I kept the change within the 400-line review budget or planned chained PRs.
- [ ] I did not mutate audio files or expand into DSP scope.
- [ ] I did not write to live Serato database V2 files.
- [ ] I ran the verification commands and they pass.
- [ ] I did not create project-root `build/` or `dist/` artifacts.
- [ ] I respected `AppState` immutability and existing architecture boundaries.

## Related documents

- `.atl/skills/gentle-ai-sdd-tdd/SKILL.md` — detailed skill instructions.
- `.planning/codebase/ARCHITECTURE.md` — architecture and agent conduct.
- `CONTRIBUTING.md` — human contributor guide.
- `openspec/config.yaml` — SDD configuration.
