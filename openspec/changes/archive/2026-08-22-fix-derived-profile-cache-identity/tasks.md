# Tasks: Fix Derived-Profile Cache Identity

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 120–180 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Implement identity-aware sibling invalidation for all three repository updaters | PR 1 | `uv run pytest -q tests/test_track_repository.py` | N/A — repository behavior is exercised by SQLite integration tests | Revert `src/xfinaudio/library/track_repository.py` and its focused tests |

## Phase 1: RED — Repository Behavior Tests

- [x] 1.1 In `tests/test_track_repository.py`, parameterize spectral, danceability, and edge-spectral updaters; add failing tests proving a changed `file_mtime_ns` or `file_size_bytes` clears both sibling profiles while retaining the requested profile.
- [x] 1.2 Add a failing matched-identity test for all three updaters proving both siblings remain unchanged.
- [x] 1.3 Add a failing missing-stat test proving requested profile persistence remains, siblings clear, identity becomes null, and cache loaders exclude the row.

## Phase 2: GREEN — Atomic Cache Identity Update

- [x] 2.1 In `src/xfinaudio/library/track_repository.py`, capture one `(mtime_ns, size_bytes)` stat result per update and keep existing serialization, rowcount, transaction, and public signatures.
- [x] 2.2 Update each explicit spectral, danceability, and edge-spectral SQL statement so sibling `CASE` values are preserved only when both captured identity fields are non-null and equal; otherwise clear both siblings, then store the captured identity atomically.
- [x] 2.3 Run `uv run pytest -q tests/test_track_repository.py` and confirm all RED scenarios pass without touching loudness, schema, audio, or serialization code.

## Phase 3: REFACTOR — Parity and Scope Check

- [x] 3.1 Review the three statements for identical identity predicates, safe parameterization, and no identifier interpolation; simplify only without changing behavior.
- [x] 3.2 Confirm focused tests cover both identity fields independently, all updater families, matched identity, missing stat, and missing-row rowcount behavior.

## Phase 4: VERIFY — Focused and Project Gates

- [x] 4.1 Re-run `uv run pytest -q tests/test_track_repository.py` as the focused proof.
- [x] 4.2 Run `uv run pytest -q`, `uv run pyright src tests`, `uv run pytest --cov --cov-fail-under=70 -q`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run python scripts/release_gate_check.py --run`; record results in `verify-report.md`.
