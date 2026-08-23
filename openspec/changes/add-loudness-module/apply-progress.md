# Apply Progress: add-loudness-module

## Status

WU1b task 1.4 is complete under strict TDD. Task 1.5 process-group cancellation and reaping remains pending.

## Completed Tasks

- [x] 1.1–1.3, 1.6–1.7 — Port, parser, fixture oracle, and duration floor (prior WU1a).
- [x] 1.4 — Executable capability preflight, typed probe-result contract, shell-free injected process execution, and typed timeout result.

## TDD Cycle Evidence

| Tasks | Test | RED | GREEN | Refactor |
|---|---|---|---|---|
| 1.4 | `tests/audio/test_loudness.py` | Correction tests against the prior adapter exposed non-executable paths, probe-status omission, and loose output matching. | `uv run pytest -q tests/audio/test_loudness.py` → 8 passed. | Structured probe result and parser helpers kept preflight isolated. |

## Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test | `uv run pytest -q tests/audio/test_loudness.py` — 8 passed. |
| Runtime harness | Deterministic injected process/probe fakes; no real bundled binary. |
| Rollback boundary | Revert the WU1b preflight/execution source, tests, tasks, progress, and notes together. |

## Remaining Tasks

- [ ] 1.5 Process-group kill, owner reaping, synchronized cancellation, and shutdown.
- [ ] WU2–WU4 (except completed governance task 4.6).
