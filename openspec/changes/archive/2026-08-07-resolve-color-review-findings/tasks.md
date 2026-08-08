# Tasks: Resolve Two-Axis Review Findings for Colour Strategies

1. [x] **Proposal** — intent, the eight findings, scope boundaries, success criteria.
2. [x] **Specification** — GIVEN/WHEN/THEN for R1–R8.
3. [x] **Design** — alternatives for F2 (carrying the anchor, and what an absent bound
   path means), F3 (which slot to displace), F6 (data over duplication), plus the
   retroactive-artifacts meta-decision.
4. [x] **Locked tracks are not anchor candidates (F1 / R1)** — `_resolve_color_anchor`'s
   first-profiled fallback skips `controls.locked_paths`.
5. [x] **Bind the anchor once (F2 / R2)** — `RecommendationCandidateContext` +
   `plan_recommendation_candidate_context` + public `resolve_color_anchor_path`;
   `recommend_playlist` gains keyword-only `color_anchor_path`; a supplied-but-absent
   path fails closed via `resolve_when_unbound=False`.
6. [x] **Control-safe anchor retention (F3 / R3)** — `build_recommendation_pool`
   displaces the last trimmable slot; all-controls pools keep the pool and drop the anchor.
7. [x] **Unconditional prerequisite warning (F4 / R4)** — `_color_filter_warnings` emits
   it whenever the bound anchor misses its gate's prerequisites.
8. [x] **Restore the informational filter warning (F5 / R5)** —
   `"{strategy} filter applied: {color}"`.
9. [x] **Dedupe the colour pair (F6 / R6)** — frozen `_ColorGate` records in
   `_COLOR_GATES`; one filter chain; `COLOR_FILTER_STRATEGIES` exported as the single
   dispatch answer and adopted at every site.
10. [x] **Public candidate-planning import (F7 / R7)** — `desktop/main_window.py` calls
    `plan_recommendation_candidate_context`.
11. [x] **Honest names and guarded math (F8 / R8)** — `_mixed_profile_close` →
    `_spectral_profile_close`; `math.isfinite` guards via `_is_finite_positive`; unused
    parameter and a `type: ignore` removed.
12. [x] **Verify** — `uv run pytest -q`, `uv run pyright src tests`, `uv run ruff check .`,
    `uv run ruff format --check .`; version 1.7.3 → 1.7.4 with `uv.lock` synced.
13. [x] **Archive** — retroactive artifacts authored from the merged commit; see
    `archive-report.md` for what was and was not synced.
