# Apply Progress: add-loudness-module

## Status

WU1 is complete under strict TDD. The next implementation boundary is WU2 persistence and
pipeline integration. The executor did not settle the supplied native runtime token.

## Completed Tasks

- [x] 1.1–1.3, 1.6–1.7 — Loudness port/profile, command/parser, conformance fixtures, and duration floor.
- [x] 1.4 — Capability preflight requires an absolute executable file with execute permission, successful typed probes, an `ebur128` filter entry, and the `true` value of the `peak` option.
- [x] 1.5 — Timeout kills then reaps the owner process; cancellation/shutdown synchronize spawn, registration, kill, and owner reaping.

## TDD Cycle Evidence

| Tasks | Test file | Layer | Safety net | RED | GREEN | Triangulate | Refactor |
|---|---|---|---|---|---|---|---|
| 1.1–1.3, 1.6–1.7 | `tests/audio/test_loudness.py` | Unit | New module | Missing-module collection failure | 5 passed | Golden, malformed, and short cases | `StrEnum` cleanup |
| 1.4 | `tests/audio/test_loudness.py` | Unit with typed probe fakes | 5 existing tests passed | Non-executable paths, non-zero probes, and unrelated `peak`/`true` text failed against the original preflight | 8 passed in commit `a90056c` | Valid vs invalid executable/probe/output cases | Extracted structured probe helpers |
| 1.5 correction | `tests/audio/test_loudness.py` | Deterministic real-thread process lifecycle | 10 passed in 1.68s | `uv run pytest -q tests/audio/test_loudness.py` → 5 failed, 10 passed: no owner reap, race let cancel/shutdown return early, and probe contract was untyped | Same command → 14 passed in 1.81s | Timeout owner-reap plus both cancel and shutdown race paths | Condition-protected lifecycle registry; focused suite remained green |

## Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test | `uv run pytest -q tests/audio/test_loudness.py` — 14 passed in 1.81s. |
| Static checks | `uv run pyright src/xfinaudio/audio/loudness.py tests/audio/test_loudness.py` — 0 errors, 0 warnings; focused Ruff check and format check passed. |
| Runtime harness | Deterministic probe/process fakes plus real Python threads exercised the factory-registration cancellation race, owner reaping, timeout classification, and process-group kill. No real FFmpeg executable ran. |
| Rollback boundary | Revert commits `a90056c` and this task-1.5 commit together to remove the WU1 runtime boundary without touching WU2+. |

## Remaining Tasks

- [ ] WU2 persistence and pipeline integration.
- [ ] WU3 target-band filter, strategy, and tag write-back.
- [ ] WU4 settings, UI surface, packaging, and full verification, except completed governance task 4.6.

## Scope Notes

- No user-library audio was touched. All WU1 process behavior is fixture/fake driven.

## Authorized Governance Reorder (4.6)

- [x] 4.6 The repository rules and README/CONTRIBUTING English/Spanish sections state that scanning remains read-only except for explicit loudness-tag writing. No WU3 behavior is implemented here.
