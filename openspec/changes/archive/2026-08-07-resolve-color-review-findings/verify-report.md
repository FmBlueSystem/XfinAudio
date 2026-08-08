# Verify Report: Resolve Two-Axis Review Findings for Colour Strategies

## Verification commands

| Command | Result |
|---|---|
| `uv run pytest -q` | PASS — 1499 passed |
| `uv run pyright src tests` | PASS — 0 errors |
| `uv run ruff check .` | PASS |
| `uv run ruff format --check .` | PASS |
| CI (PR #339) | PASS — green on merge |

The 1499 figure is the suite at `201e001`. The successor change
`prep-copilot-color-anchor` (PR #340) added six tests, taking the suite to 1505 — the
count that reproduces on `main` today.

## Requirement verification

| Requirement | Evidence | Status |
|---|---|---|
| R1. Locked tracks are never the anchor | `tests/test_playlist_service.py::test_color_anchor_resolution_never_selects_a_locked_track`; `_resolve_color_anchor` guards its first-profiled scan with `candidate.path not in controls.locked_paths` | PASS |
| R2. Anchor bound once and carried | `tests/test_application_recommendation_candidates.py::test_context_planner_binds_an_anchor_for_same_color_too` (bound at planning time); `tests/test_playlist_service.py::test_final_enforcement_uses_bound_anchor_path_for_same_color` (final pass uses that identity); `::test_supplied_missing_anchor_path_fails_closed_for_same_color` (absent path fails closed, does not re-resolve) | PASS |
| R3. Anchor retention never displaces a control | `tests/test_candidate_pool.py::test_protected_anchor_never_displaces_a_control_track`; `build_recommendation_pool` selects the displaced index from `trimmable` only, and returns the pool unchanged when `trimmable` is empty | PASS |
| R4. Unconditional prerequisite warning | `tests/test_playlist_service.py::test_same_color_prerequisite_warning_is_emitted_without_generated_candidates` and `::test_same_color_energy_prerequisite_warning_is_emitted_without_generated_candidates` — both assert the warning with an empty generated pool, the case the conditional emission used to swallow | PASS |
| R5. Informational filter warning restored | `tests/test_playlist_service.py::test_same_color_emits_the_filter_applied_informational_warning` and `::test_same_color_energy_emits_the_filter_applied_informational_warning` | PASS |
| R6. One filter, one dispatch answer | `tests/test_recommendation_service_state.py::test_recommend_uses_context_callback_for_every_colour_strategy` is parametrized over both colour strategies against one code path; `::test_recommend_uses_records_route_for_ordinary_strategy` guards the ordinary path. `COLOR_FILTER_STRATEGIES` is the only membership test at all four dispatch sites | PASS |
| R7. Public candidate-planning import | `src/xfinaudio/desktop/main_window.py` imports `plan_recommendation_candidate_context` from `xfinaudio.application.recommendation_candidates`; the symbol is listed in that module's `__all__` | PASS |
| R8. Honest names, guarded math | `_spectral_profile_close` (renamed) is applied to every dominant-colour label; `_is_finite_positive` plus `math.isfinite` guards in `_relative_delta` and the RGB comparison reject non-finite features. Covered indirectly by the per-colour gate tests inherited from `tighten-spectral-color-filters` | PASS |

## Non-functional verification

- One pre-existing test pinned a deliberately-replaced contract and was **re-authored
  with an inline reason, not deleted** — see `apply-progress.md` → "Characterization
  exception". No other existing test changed behaviourally.
- Review budget: ~180 production + ~290 test changed lines, within the 400-line budget.

## Out of scope confirmation

- The bounded gate's thresholds and predicates are unchanged from
  `tighten-spectral-color-filters`.
- `PrepCopilotController` was **not** fixed here; it still planned colour sets
  unanchored at merge time. Explicitly deferred and shipped as
  `prep-copilot-color-anchor` (PR #340).
