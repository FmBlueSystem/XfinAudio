---
name: gentle-ai-sdd-tdd
description: Use when planning or implementing any XfinAudio behavior change to enforce the gentle-ai SDD/TDD lifecycle.
---

## When to use

Trigger this skill for every behavior change, feature, non-trivial refactor, or bug fix in XfinAudio. Do not use it for pure docs typo fixes or one-line formatting changes that touch no behavior.

## What gentle-ai SDD/TDD means here

- **SDD**: Spec-Driven Development. Every change produces durable artifacts under `openspec/`.
- **TDD**: Test-Driven Development. Every behavior-changing task follows RED → GREEN → REFACTOR → VERIFY.
- **gentle-ai**: The change is executed incrementally by AI agents with explicit phase gates, not in a single monolithic patch.

## SDD lifecycle

Run these phases in order. Do not skip a phase because the change "looks small".

1. **Proposal** — `proposal.md`
   - Intent, scope, in/out, risks, rollback plan, success criteria.
   - If the change exceeds 400 changed lines, declare chained PRs.

2. **Specification** — `spec.md`
   - GIVEN/WHEN/THEN scenarios per requirement.
   - No implementation details; only observable behavior.

3. **Design** — `design.md`
   - Architecture impact, affected files, data model changes, safety considerations.

4. **Tasks** — `tasks.md`
   - Numbered, verifiable work units.
   - Mark TDD cycles explicitly: RED, GREEN, REFACTOR, VERIFY.

5. **Apply**
   - Implement the smallest change that satisfies the spec.
   - In strict TDD, write or update the failing test first.

6. **Verify**
   - Run all verification commands.
   - Produce `verify-report.md` with requirement-by-requirement evidence.

## TDD cycle

For every behavior-changing task:

1. **RED**: add or update a failing test that proves the intended behavior is missing.
2. **GREEN**: implement the smallest production change that makes the test pass.
3. **REFACTOR**: clean up duplication, naming, or structure while keeping tests green.
4. **VERIFY**: run the focused test, then the full verification suite.

## Required state artifact

Every active SDD change must have an `openspec/changes/<change-name>/state.yaml`:

```yaml
schema: gentle-ai.sdd-state.v1
change: <change-name>
artifact_store: openspec
status: <phase>
created: YYYY-MM-DD
updated: YYYY-MM-DD
strict_tdd: true
phases:
  proposal: complete
  specs: complete
  design: complete
  tasks: complete
  apply: in-progress
  verify: pending
next_recommended: apply
blocked_reasons: []
delivery:
  strategy: auto-chain
  chained_prs_recommended: false
  chain_strategy: feature-branch-chain
  review_budget_changed_lines: 400
notes:
  - Implementation must proceed by PR slice, not as one monolithic patch.
  - Behavior-changing tasks require RED -> GREEN -> REFACTOR.
```

Update `status`, `updated`, and the current phase after every session.

## Hard rules

- Do not implement during SDD initialization or proposal/spec/design phases.
- Do not write production code before a failing test in strict TDD mode.
- Do not exceed the 400-line review budget without an explicit chained-PR plan.
- Do not mutate audio files.
- Do not add DSP, audio rendering, mixing, time-stretching, pitch-shifting, or waveform analysis.
- Do not write to live Serato database V2 files; crate exports stay behind the safe flow.
- Do not add dependencies without upper bounds in `pyproject.toml` and a locked `uv.lock` update.
- Do not mutate `AppState` in place; always use `model_copy(update=...)`.

## Verification commands

Run these in order before declaring any task or change complete:

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/release_gate_check.py --run
```

For focused work, run the smallest relevant `pytest` target first, then the full suite.

## Definition of done for a change

- [ ] `proposal.md`, `spec.md`, `design.md`, `tasks.md`, `apply-progress.md`, and `verify-report.md` exist and are coherent.
- [ ] `state.yaml` reflects the current phase.
- [ ] All verification commands pass.
- [ ] No project-root `build/` or `dist/` artifacts were created.
- [ ] Safety constraints (no audio mutation, no DSP, no Serato V2 writes) are respected.
- [ ] Commit messages use conventional commits without AI attribution.

## Related project documents

- `openspec/config.yaml` — project-level SDD configuration.
- `.planning/codebase/ARCHITECTURE.md` — architecture and agent conduct.
- `CONTRIBUTING.md` — human contributor guide.
