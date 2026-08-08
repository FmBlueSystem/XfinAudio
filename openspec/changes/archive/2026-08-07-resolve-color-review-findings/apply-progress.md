# Apply Progress: Resolve Two-Axis Review Findings for Colour Strategies

Shipped as PR #339, squashed to `201e001` on 2026-08-07 (branch commit `f7dd244`).

## Completed

- [x] **F1** — `_resolve_color_anchor`'s first-profiled fallback now skips
      `controls.locked_paths`. The candidate pool puts every control at the front, so
      the previous unfiltered scan made a locked track the anchor whenever no
      start-path or manual-prefix control named one.
- [x] **F2** — `RecommendationCandidateContext(records, color_anchor_path)` and
      `plan_recommendation_candidate_context` bind the anchor from the **pre-anchor**
      pool, before prefilter/dedupe/cap reshape it.
      `recommend_playlist(..., color_anchor_path=...)` binds that exact path via
      `_bind_supplied_anchor`; when the path is supplied but absent, it passes
      `resolve_when_unbound=False` so `_apply_color_filter` fails closed instead of
      re-resolving. `plan_recommendation_candidates` delegates to the new planner for
      colour strategies, so the two entry points cannot disagree.
- [x] **F3** — `build_recommendation_pool`'s protected-path retention is control-aware:
      it displaces the last index **not** in `preserved_control_paths(controls)`. An
      empty pool returns the anchor alone; an all-controls pool is returned unchanged
      and the anchor is not retained (the gate already fails closed on a missing anchor,
      whereas evicting a control makes `apply_controls` reject the request downstream).
      `dedupe_recommendation_duplicates` likewise treats the bound anchor as protected.
- [x] **F4** — `_color_filter_warnings` emits the prerequisite warning unconditionally
      when `_anchor_meets_prerequisites` fails, using the gate's own
      `missing_prerequisite` wording.
- [x] **F5** — the `"{strategy} filter applied: {color}"` informational warning is back,
      naming the bound anchor's dominant colour.
- [x] **F6** — the `same_color` / `same_color_energy` pair collapsed behind frozen
      `_ColorGate` records (`match_energy`, `reports_shortage`, `missing_prerequisite`,
      `exclusion_reason`) in `_COLOR_GATES`, consumed by one
      `_apply_color_filter` / `_color_eligible` / `_color_filter_warnings` chain.
      `COLOR_FILTER_STRATEGIES = frozenset(_COLOR_GATES)` is exported and adopted by
      every dispatch site: `recommend_playlist`, `prefilter_strategy_candidates`,
      `application/recommendation_candidates.py`, and `desktop/recommendation_service.py`.
- [x] **F7** — `desktop/main_window.py` imports the public
      `plan_recommendation_candidate_context` instead of a private cross-package symbol.
- [x] **F8** — `_mixed_profile_close` renamed `_spectral_profile_close` (it applies to
      every dominant-colour label, not just MIXED); `_is_finite_positive` and
      `math.isfinite` guards added so NaN/infinite spectral features fail closed instead
      of reading as "not close"; one unused parameter and one `type: ignore` removed.
- [x] **Wiring** — `MainWindow._desktop_color_anchor_candidate_context` added and wired
      into `RecommendationService` via `window_service_wiring.py`;
      `PlaylistWorkflowService`'s `same_color_energy_anchor_path` renamed to the
      strategy-neutral `color_anchor_path`.

## Test evidence

| Finding | Test file | Test name(s) |
|---|---|---|
| F1 / R1 | `tests/test_playlist_service.py` | `test_color_anchor_resolution_never_selects_a_locked_track` |
| F2 / R2 | `tests/test_application_recommendation_candidates.py` | `test_context_planner_binds_an_anchor_for_same_color_too` |
| F2 / R2 | `tests/test_playlist_service.py` | `test_final_enforcement_uses_bound_anchor_path_for_same_color`, `test_supplied_missing_anchor_path_fails_closed_for_same_color` |
| F3 / R3 | `tests/test_candidate_pool.py` | `test_protected_anchor_never_displaces_a_control_track` |
| F4 / R4 | `tests/test_playlist_service.py` | `test_same_color_prerequisite_warning_is_emitted_without_generated_candidates`, `test_same_color_energy_prerequisite_warning_is_emitted_without_generated_candidates` |
| F5 / R5 | `tests/test_playlist_service.py` | `test_same_color_emits_the_filter_applied_informational_warning`, `test_same_color_energy_emits_the_filter_applied_informational_warning` |
| F6 / R6 | `tests/test_recommendation_service_state.py` | `test_recommend_uses_context_callback_for_every_colour_strategy` (parametrized over both colour strategies), `test_recommend_uses_records_route_for_ordinary_strategy` |

## Characterization exception

`tests/test_recommendation_service_state.py::test_recommend_uses_context_callback_for_every_colour_strategy`
was **re-authored, not deleted**. It previously pinned `same_color` on the plain records
route — the exact contract F2 replaces, because that route re-resolved the anchor after
dedupe/cap. Its docstring carries the reason inline.

## Deviations from design

None. Implementation matches `design.md`, including the deliberate distinction between
`color_anchor_path=None` (nothing bound → resolve internally) and a supplied path that
is absent from the pool (fail closed).

## Verification

- ✅ `uv run pytest -q` — 1499 passed.
- ✅ `uv run pyright src tests` — 0 errors.
- ✅ `uv run ruff check .` / `uv run ruff format --check .` — clean.
- ✅ CI green on PR #339.
- ✅ Version 1.7.3 → 1.7.4; `uv.lock` diff is version-only.

## Known gap at merge time (fixed separately)

`PrepCopilotController.generate` still took the plain records route for every strategy,
so Prep Copilot planned colour sets **unanchored** while the main desktop recommendation
route did not. Out of scope here; shipped as `prep-copilot-color-anchor` (PR #340).
