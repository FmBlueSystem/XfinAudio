# Apply Progress: add-loudness-module

## Status

WU1 and WU2 tasks 2.1, 2.2, and 2.4 are complete under strict TDD. Sibling preservation and
pipeline integration remain pending. The executor did not settle the supplied native runtime token.

## Completed Tasks

- [x] 1.1–1.3, 1.6–1.7 — Loudness port/profile, command/parser, conformance fixtures, and duration floor.
- [x] 1.4 — Capability preflight requires an absolute executable file with execute permission, successful typed probes, an `ebur128` filter entry, and the `true` value of the `peak` option.
- [x] 1.5 — Timeout kills then reaps the owner process; cancellation/shutdown synchronize spawn, registration, kill, and owner reaping.
- [x] 2.1 — Nullable `loudness_profile_json` migration and explicit scan upsert `CASE` preserve an existing payload on ordinary rescans.
- [x] 2.2 — Versioned profile JSON cache checks its own post-write mtime/size against disk, not shared track identity.
- [x] 2.4 — Typed failures persist/cache on unchanged inputs; explicit force reanalysis bypasses the cache.

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

## WU2a Task 2.1 Evidence

| Task | Safety net | RED | GREEN | Refactor |
|---|---|---|---|---|
| 2.1 | `uv run pytest -q tests/test_track_repository.py` → 75 passed in 0.67s | Same command → 2 failed, 75 passed: missing column blocked direct payload seed and current-version migration | Same command → 77 passed in 0.58s | Existing nullable-column migration pattern retained; no `SCHEMA_VERSION` bump. |

| Evidence | Result |
|---|---|
| Focused tests | `uv run pytest -q tests/test_track_repository.py` — 77 passed in 0.58s. |
| Runtime harness | SQLite file integration: seed a profile JSON directly, run `save_scan_results`, then read the same column back. |
| Rollback boundary | Revert the WU2a commit to remove only the nullable column and scan-upsert preservation branch. |

## WU2a Maintainer Budget

The maintainer constrained this objective to **330 text changed lines**, including tests and SDD artifacts, to reserve correction margin. This slice is limited to task 2.1; it deliberately does not load/cache loudness profiles or implement identity, retry, pipeline, tag, strategy, or UI behavior.

## WU2b Tasks 2.2 and 2.4 Evidence

| Tasks | Safety net | RED | GREEN | Refactor |
|---|---|---|---|---|
| 2.2, 2.4 | `uv run pytest -q tests/test_track_repository.py` → 77 passed in 0.62s | Same command → 5 failed, 77 passed: no loudness cache API | Same command → 82 passed in 0.65s | Shared serializer/deserializer keeps malformed JSON fail-closed. |

| Evidence | Result |
|---|---|
| Focused tests | `uv run pytest -q tests/test_track_repository.py` — 82 passed in 0.65s. |
| Runtime harness | SQLite cache tests use a real temporary file, mutate only shared DB identity, and prove profile-owned identity remains decisive. |
| Rollback boundary | Revert the WU2b commit to remove `TrackRecord.loudness_profile` and repository cache behavior without affecting WU2a schema migration. |

## Remaining Tasks

- [ ] WU2 tasks 2.3 and 2.5: sibling preservation and pipeline integration.
- [ ] WU3 target-band filter, strategy, and tag write-back.
- [ ] WU4 settings, UI surface, packaging, and full verification, except completed governance task 4.6.

## Scope Notes

- No user-library audio was touched. All WU1 process behavior is fixture/fake driven.

## Authorized Governance Reorder (4.6)

- [x] 4.6 The repository rules and README/CONTRIBUTING English/Spanish sections state that scanning remains read-only except for explicit loudness-tag writing. No WU3 behavior is implemented here.

## WU1 Self-Verification — HEAD `202f6fc`

Read-only self-verification completed on 2026-08-22. All requested WU1 gates passed in order; coverage and the release gate were intentionally not run.

| Command | Exit | Pytest/tool result | Wall time | Exact combined-output SHA-256 |
|---|---:|---|---:|---|
| `uv run pytest -q tests/audio/test_loudness.py` | 0 | 14 passed in 1.81s | 3.413s | `sha256:7289061d73e890a291aae88043005e2f17f001fce8381fc6cc7840586dfca78c` |
| `uv run pytest -q` | 0 | 1706 passed, 266 warnings in 32.00s | 35.190s | `sha256:ab3c020f50be511745b388161ef1084af6c3aa26ab2499ac23a6a58fc6a1e449` |
| `uv run pyright src tests` | 0 | 0 errors, 0 warnings, 0 informations | 5.244s | `sha256:3c1a00ce86bcdce1ef7ba97d18d9c5b4e7026f49a5dc61a23382ed7345e02316` |
| `uv run ruff check .` | 0 | All checks passed | 0.115s | `sha256:82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| `uv run ruff format --check .` | 0 | 290 files already formatted | 0.054s | `sha256:aed20c5cdfe9f925fe3d0e35cc2b37455ed39da2dab16a5441a0d6530c2e51af` |

Verification file-drift audit:

- `uv run` transiently changed only the editable-project version in `uv.lock` from 1.8.0 to 1.8.2; the verifier restored that version-only drift to HEAD.
- `docs/reviews/loudness-module-review.md` remained untracked and byte-identical at `sha256:cca5dfd5a0111d59c5280fee9913fbcb40badf6f9c4ac2603b772a19e0e0fdb9`.
- No source or test file changed during self-verification, and project-root `build/` and `dist/` remained absent.

## Native Runtime Status After WU1

Settlement recorded the WU1 evidence as passed but returned `maintainer_decision`: the
fresh-context correction made the final WU1b candidate 560 changed lines against the native
400-line objective, although the implementation and correction commits are independently
303 and 399 changed text lines. Further runtime work is stopped at ledger revision
`sha256:d941ab0d243c9804d1f79fc3aa845bc725019a2f34af87a20dfcad2f139718c6` pending the exact
maintainer reset documented in `IMPLEMENTATION-NOTES.md`.
