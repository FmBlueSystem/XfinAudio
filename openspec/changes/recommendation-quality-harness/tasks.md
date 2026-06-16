# Tasks: Recommendation Quality Harness and Pool-Collapse Fix

## PR 1 — Evaluation harness (read-only)

1. [x] **Proposal** — Arbor analysis + best route (H1a + H2b).
2. [x] **Specification** — GIVEN/WHEN/THEN for metrics and fix.
3. [x] **Design** — module seam, metric definitions, scorer independence.
3b. [x] **Refactor: relocate `build_recommendation_pool`** to `recommendation/pool.py`; presenter
        re-exports. Existing presenter tests stay green (no behavior change). Avoids the latent
        `quality` import cycle and Qt in the harness.
4. [x] **TDD: transition validity oracle** — `_transition_valid` (Camelot adjacency + BPM ≤ 3%).
5. [x] **TDD: fill-rate + collapse** — `_fill_rate` and collapse count.
6. [x] **TDD: energy monotonicity** — ascending strategies; `None` otherwise.
7. [x] **TDD: deterministic anchor sampling** — seeded `_sample_anchors`.
8. [x] **TDD: evaluate_recommendations orchestration** — `EvalReport` via real pool + recommend.
9. [x] **TDD: report render determinism** — `EvalReport.render()`.
10. [x] **CLI smoke** — `scripts/eval_recommendation.py` against a temp SQLite DB.
11. [x] **Baseline run** — saved to `baseline-report.md` (40 anchors, real library).
12. [x] **VERIFY (PR1)** — 877 passed; pyright 0 errors; ruff clean.
13. [ ] **Commit + PR 1** — conventional commit, link issue.

## PR 2 — Filtered-strategy collapse fix (REVISED by PR1 baseline evidence)

> Baseline finding: collapse is concentrated in range-filtered strategies (chill 35/40,
> warmup 16/40, peak_time 7/40), NOT in `build_recommendation_pool` (harmonic_journey/same_vibe
> share the pool and reach fill=1.0). Target the range-filter + BPM-jump-guard interaction in
> `playlist_service` for filtered strategies.

14. [x] **TDD: collapse reproduction** — strategy-aware pool tests + start_path crash test (RED).
15. [x] **GREEN: collapse fix** — strategy-aware `build_recommendation_pool` (pre-filter by
        energy/BPM range) + start_path/end_path exempt from BPM-jump guard. Wired into desktop
        (coordinator, prep_copilot) and harness.
15b. [x] **chill optimizer-backed** — removed bpm_ascending sort so chill sequences harmonically;
         raised harmonic weight 0.30→0.40. Recovers validity 0.269→0.476.
16. [x] **REFACTOR** — all strategy/presenter/service tests green.
17. [x] **Before/after measurement** — recorded in verify-report.md (warmup/peak_time collapse→0;
        chill 35→2; chill validity recovered via optimizer-backing).
18. [x] **VERIFY** — 882 passed; pyright 0; coverage 89.68%; ruff clean; release gate PASS.
19. [ ] **Commit + PRs** — conventional commits, link issue (awaiting user go-ahead).

## Archive

20. [ ] **Archive** — sync delta specs and move change to archive after PRs land.
