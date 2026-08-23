# Verification Report: Watcher-Loudness Integration

## Requirement evidence

| Requirement | Evidence | Result |
| --- | --- | --- |
| App-owned tag-write events do not surface Rescan | `test_loudness_tag_write_events_are_suppressed_but_external_changes_and_expiry_surface` | PASS |
| External modifications remain visible | Same deterministic integration test fires a different path and settles it | PASS |
| Suppression expires | Same test advances an injected monotonic clock, then detects the original path | PASS |
| Suppression precedes and targets the tag writer exactly | `test_completion_suppresses_the_exact_tag_target_before_writing` | PASS |
| Desktop runtime has one wired/stopped watcher | `test_window_factory_wires_one_watcher_to_scan_and_loudness_and_stops_it` | PASS |

## Strict TDD evidence

RED was recorded before production changes: the focused test command failed
with two expected constructor errors for absent `monotonic_clock` and
`path_suppressor` seams. GREEN then passed 28 focused tests. The final focused
selection passed 21 tests after composition and formatting changes.

## Final verification — 2026-08-23

1. `uv run pytest -q` — **1855 passed, 45 warnings** (60.89s).
2. `uv run pyright src tests` — **0 errors, 0 warnings, 0 informations**.
3. `uv run pytest --cov --cov-fail-under=70 -q` — **1855 passed, 45 warnings; 91.36% coverage**.
4. `uv run ruff check .` — **All checks passed**.
5. `uv run ruff format --check .` — **307 files already formatted**.
6. `uv run python scripts/release_gate_check.py --run` — **exit 0**; tests/coverage, type-check, lint, format, release readiness, publication/source-package hygiene, PyInstaller check-only, and root artifact hygiene passed. The gate records real Mixed In Key audio QA as completed.

## Runtime harness

N/A. The test boundary uses deterministic fake filesystem events, debounce
timers, and a monotonic clock rather than a real OS observer; the release gate
covers the project runtime smoke separately.

## Rollback

Revert `5336e42` to remove the bounded suppression and watcher composition.
No recommendation, audio-analysis, or scan business logic is changed.
