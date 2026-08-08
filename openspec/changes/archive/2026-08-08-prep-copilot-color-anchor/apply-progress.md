# Apply Progress: Carry the Bound Colour Anchor Through Prep Copilot Variant Planning

Shipped as PR #340, squashed to `53d68a6` on 2026-08-08 (branch commit `2c2bd0d`).

## Completed

- [x] **G1** — `PrepCopilotController.generate` tests the strategy against
      `COLOR_FILTER_STRATEGIES` and, for a colour strategy, takes
      `self._state._desktop_color_anchor_candidate_context(controls, strategy_name)`,
      reading `context.records` and `context.color_anchor_path`. Every other strategy
      keeps the byte-identical `_desktop_recommendation_records` route with
      `color_anchor_path = None`.
- [x] **G2** — `_internal_strategy_name` normalises whatever the combo yields via
      `resolve_strategy_name`. `currentData()` is empty for combos populated without
      user data, so the caller falls back to the display label; `"Same Color"` is not an
      internal strategy name, so the unnormalised membership test silently skipped the
      colour branch. Unresolvable text is passed through untouched — it already fails
      downstream in `recommend_playlist` as a reported error, and raising here would turn
      that into an unhandled exception in the UI.
- [x] **G3** — keyword-only `color_anchor_path` added to `generate_prep_copilot_plan`,
      `build_prep_copilot_plan` and `_build_variant`, and passed into `recommend_playlist`
      for all three variants. `generate_prep_copilot_plan` forwards it **unconditionally**:
      `None` is exactly what tells the builder to resolve an anchor itself, which is what
      the non-colour route wants, so the previous conditional forwarding collapsed.
- [x] **G4** — `application.prep_copilot.PlanBuilder` and
      `desktop.prep_copilot.PlanGenerationBuilder` retyped from
      `Callable[[list[TrackRecord], DJSetIntent], PrepCopilotPlan]` and
      `Callable[..., Any]` to `Protocol`s whose `__call__` declares
      `*, color_anchor_path: str | None = None`. An injected builder that cannot accept
      the bound anchor is now a type error at the seam instead of a `TypeError` at
      generation time.
- [x] **Deliberate non-changes** — `DJSetIntent` and `PrepCopilotGenerationRequest` do
      **not** gain the anchor. Docstrings on `generate_prep_copilot_plan` and
      `build_prep_copilot_plan` record why: the intent and the request model what the
      human asked for, the anchor path is machine-bound identity.

## Test evidence

| Requirement | Test file | Test name(s) |
|---|---|---|
| R1 | `tests/test_prep_copilot_controller.py` | `test_controller_routes_colour_strategies_through_the_bound_anchor_context` — asserts the context route fired once with `"same_color"`, the plain route never fired, and the generation call received the context's records and `/music/anchor.flac` |
| R2 | `tests/test_prep_copilot_controller.py` | `test_controller_routes_colour_display_labels_through_the_bound_anchor_context` — combo with `currentData()` empty and text `"Same Color"`; also asserts the request's `strategy` is the internal `"same_color"` |
| R3 (fail closed, `same_color`) | `tests/test_prep_copilot.py` | `test_variant_that_filters_out_the_bound_colour_anchor_fails_closed` |
| R3 (fail closed, both axes) | `tests/test_prep_copilot.py` | `test_same_color_energy_variant_that_filters_out_the_bound_anchor_fails_closed` — the pool makes the energy predicate load-bearing: one candidate matches colour but not energy, the other energy but not colour, so the anchor-keeping variant proves the gate is anchored rather than merely non-empty |
| R3 (all three variants) | `tests/test_prep_copilot.py` | `test_build_prep_copilot_plan_forwards_the_bound_anchor_to_every_variant` — monkeypatches `recommend_playlist` and asserts the forwarded list is `["/music/anchor.flac"] * 3` |
| R4 | `tests/test_prep_copilot_controller.py` | `test_controller_lets_an_unbound_colour_anchor_fall_back_to_internal_resolution` — runs the **real** generation chain with `color_anchor_path=None`; every variant returns tracks and the off-colour candidate is excluded, proving internal resolution ran instead of failing closed |
| R5 | `tests/test_application_prep_copilot.py` | `test_application_prep_copilot_generation_builds_intent_and_delegates` (stub signature updated to the Protocol's keyword contract) |

A shared `spectral_track` helper was added to `tests/test_prep_copilot.py` and imported
by the controller tests. It gives RGB tracks finite positive `centroid_hz` / `rolloff_hz`
(1000.0 / 2000.0) so same-label candidates share the bounded gate's relative-delta
denominators — `SpectralProfile` defaults both to `0.0`, which fails the gate closed and
would make every one of these tests vacuously "empty".

## Deviations from design

None.

## Verification

- ✅ `uv run pytest -q` — 1505 passed (1499 before, plus the 6 tests above).
- ✅ `uv run pyright src tests` — 0 errors.
- ✅ `uv run ruff check .` / `uv run ruff format --check .` — clean.
- ✅ CI green on PR #340.
- ✅ Version 1.7.4 → 1.7.5; `uv.lock` diff is version-only.

## Known gaps at merge time (fixed separately)

1. `PrepCopilotController.generate` and `RecommendationService.recommend` now held
   near-verbatim copies of the same colour-route branch.
2. `PrepCopilotController` reached two private `MainWindow` methods through `_state`,
   while `RecommendationService` took the same two as injected callables.

Both closed on `chore/color-anchor-followups`; see `archive-report.md` → "Follow-Up Items".
