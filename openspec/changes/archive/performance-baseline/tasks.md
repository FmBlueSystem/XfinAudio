# Tasks: Performance Baseline

## Task 1 — Fixture generator

- [ ] Create `tests/fixtures/performance_tracks.py` with `make_complete_tracks(count)`.

## Task 2 — Baseline tests

- [ ] Create `tests/test_performance_baseline.py`.
- [ ] Measure `recommend_playlist()` for 100 and 500 tracks.
- [ ] Measure in-memory JSON/CSV/M3U export.
- [ ] Measure quality report and DJ readiness report generation.
- [ ] Assert elapsed times are under generous thresholds.

## Task 3 — Reporter script

- [ ] Create `scripts/performance_baseline.py`.
- [ ] Run the same scenarios and print a Markdown table.
- [ ] Exit non-zero on threshold violation.

## Task 4 — Verify

- [ ] Run focused and full pytest suites.
- [ ] Run reporter script.
- [ ] Run pyright, coverage, ruff check/format.
- [ ] Run `scripts/release_gate_check.py --run`.
