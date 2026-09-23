# Tasks: arc-subset-sequencing

## WU1 — Rescue port from the stale branch

- [x] 1.1 Locate the uncommitted arc-subset work on `feat/library-file-watcher-integration`
      in `/Users/freddymolina/Documents/xfinaudio-local-main` (68 commits behind `main`)
- [x] 1.2 Port `src/xfinaudio/recommendation/optimizer.py` and
      `tests/test_sequence_optimizer.py` byte-identically via `git apply` (both files were
      unchanged between the stale branch's base and `main`), and port
      `src/xfinaudio/recommendation/playlist_service.py` and
      `tests/test_playlist_service.py` via 3-way merge (`main` had independently added the
      loudness band filter to `playlist_service.py`); the port reproduces exactly 999
      insertions
- [x] 1.3 Port `tests/test_sequence_optimizer.py` and `tests/test_playlist_service.py`
      additions

## WU2 — Optimizer: arc-subset primitive

- [x] 2.1 `recommend_sequence` routing branch (arc strategy + BPM ceiling + sized arc
      length → `_arc_subset_recommendation`); `arc_length=None` falls back to the legacy
      solvers
- [x] 2.2 Hybrid solver: `_exact_arc_subset_path` (target-length bitmask DP) and
      `_beam_arc_subset_path` (deterministic beam, stable tie-breaking, widened retry on
      small capped domains)
- [x] 2.3 Lazy scoring: per-edge cached `transition()` closure, `_lazy_arc_bonus` with
      feasible-domain normalization; no `_score_matrix`/`_arc_bonuses` on the reachable
      pool
- [x] 2.4 Feasibility-aware pool sizing: `_lazy_bpm_neighbors` (folded `b/2`, `b`, `2b`
      windows via `bpm_difference_percent`), `_reachable_indices`, `_hop_distances`
      pruning; no blind truncation
- [x] 2.5 Mandatory-path fail-closed handling (missing, exceeding target, non-coexistent)
      and proven-infeasible vs. budget-exhausted warning distinction
- [x] 2.6 Manual-prefix accounting surface: `target_length`, `mandatory_paths`,
      `external_start`, `arc_slot_offset` parameters

## WU3 — Playlist service integration

- [x] 3.1 Stop pre-truncating via `_shortlist_for_sequencing` on the arc branch only;
      every other caller unaffected
- [x] 3.2 `_expected_arc_subset_length`: size the arc by played-slot durations; thread
      `target_length`, `mandatory_paths = preserved_control_paths(controls) - manual_paths`,
      `external_start = manual_prefix[-1]`, `arc_slot_offset = len(manual_prefix)`
- [x] 3.3 Thread subset warnings from `recommend_sequence` into `recommend_playlist`
      warnings

## WU4 — Tests (strict TDD per SPEC-WU25 items 1–13)

- [x] 4.1 Fragmented-shortlist collapse regression
      (`test_energy_arc_does_not_collapse_on_a_fragmented_shortlist`)
- [x] 4.2 BPM-ceiling property, `end_path` reserve/unreachable, proven-infeasible vs.
      budget-exhausted distinction (tests 2–4)
- [x] 4.3 Mandatory controls: locked/manual seam, exceed-target, non-coexistence,
      missing-from-pool (test 5)
- [x] 4.4 Edge cases: `None` start, missing BPM, uncapped fallback, one-track
      start==end (test 6)
- [x] 4.5 Folded 2:1 neighbor discovery (test 7)
- [x] 4.6 Exact + beam determinism and observability (test 8)
- [x] 4.7 Legacy no-regression: non-arc call shapes keep legacy solvers; non-arc
      strategies bypass subset search (tests 9, 12)
- [x] 4.8 Performance guards: no eager matrices, bounded beam scoring, exploration cache
      discipline, domain-aware normalization (test 10)
- [x] 4.9 End-to-end service tests: raw vs. desktop-capped pool per arc strategy,
      anchor/locked/manual-prefix preservation (tests 11, 13)

## WU5 — Local validation (measured on this branch)

- [x] 5.1 Focused suites, full suite, coverage, pyright, ruff check/format — evidence in
      `verify-report.md`

## WU6 — Verification and governance

- [x] 6.1 Aggregate 40-anchor before/after re-measurement (all four strategies, desktop-
      capped and raw conditions) against a **scratch copy** of the SQLite library,
      `target_count=12`, by `scripts/arc_subset_benchmark.py`. Raw condition: 3-10 of 40
      full sets before, 40 of 40 after. Desktop condition: `peak_time` 33 of 40 before,
      39 after. The fix also costs more — 4.7x overall, up to 13.7x in the raw condition
      — and the cost table is recorded in `verify-report.md`.
- [x] 6.2 Required-properties verification — **RE-SCOPED, not completed as written.**
      SPEC-WU25 is unrecoverable (a local-only file in a deleted clone, present in no ref
      of this repository), so its items 1-13 cannot be confirmed. Replaced by verifying
      that every scenario of this change's own spec delta names a pinning test that exists
      and passes: 15 scenarios, 22 test names. Weaker than the original item; the reason is
      recorded in `verify-report.md`.
- [x] 6.3 Independent verification of this change — the gates re-measured by a different
      session on the same branch: 1901 passed, 91.58%, pyright 0 errors / 0 warnings, ruff
      clean.
- [ ] 6.4 Review-budget decision per AGENTS.md: chained-PR plan or a recorded explicit
      accept for ~999 changed lines (budget 400). The owner's decision; the only open item.

## Deferred / out of scope

- BPM metadata parsing or correction (documented half-time incident doubled 1,297 real
  BPMs; never revisit under any framing)
- `_bpm_reachable_from` algorithm, non-arc strategies, existing thresholds,
  `energy_arc.py` shape functions
