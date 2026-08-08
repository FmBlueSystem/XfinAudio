# Specification: Resolve Two-Axis Review Findings for Colour Strategies

## Requirements

### R1. A locked track never becomes the colour anchor (F1)

**GIVEN** `DJControls(locked_paths=[...])` and no start-path or manual-prefix control
carrying a spectral profile
**WHEN** `_resolve_color_anchor` falls through to its first-profiled scan
**THEN** it skips every path in `controls.locked_paths` and binds the first profiled
non-locked record instead, because locked tracks are preserved exceptions rather than
anchor candidates.

### R2. The colour anchor is bound once and carried (F2)

**GIVEN** a colour strategy (`same_color` or `same_color_energy`)
**WHEN** `plan_recommendation_candidate_context` plans the pool
**THEN** it resolves the anchor from the **pre-anchor** candidate pool, before
`prefilter_strategy_candidates`, dedupe and cap reshape it, and returns that path
alongside the records in a `RecommendationCandidateContext`.

**GIVEN** `recommend_playlist(..., color_anchor_path=<path>)`
**WHEN** `<path>` is present in the pool
**THEN** the gate measures every candidate against that exact track, not a re-resolved one.

**GIVEN** `recommend_playlist(..., color_anchor_path=<path>)`
**WHEN** `<path>` is absent from the pool
**THEN** the gate **fails closed** (drops every generated candidate) instead of
re-resolving a different anchor.

**GIVEN** `color_anchor_path=None`
**THEN** behaviour is unchanged: the gate resolves an anchor itself.

### R3. Retaining the protected anchor never displaces a control (F3)

**GIVEN** a capped pool that must retain a protected colour anchor
**WHEN** `build_recommendation_pool` makes room for it
**THEN** it displaces the last **trimmable** slot — one whose path is not in
`preserved_control_paths(controls)` — and preserves the relative order of the rest.

**GIVEN** a pool made entirely of controls, with no trimmable slot
**THEN** the pool is returned unchanged and the anchor is simply not retained; the
colour gate already fails closed on a missing anchor, whereas evicting a control would
make `apply_controls` reject the request downstream.

**GIVEN** an empty pool
**THEN** the result is the protected anchor alone.

### R4. The prerequisite warning is unconditional (F4)

**GIVEN** a colour strategy whose bound anchor carries no spectral profile (or, for
`same_color_energy`, no energy level)
**WHEN** `recommend_playlist` builds its warnings
**THEN** the prerequisite warning naming that gate's `missing_prerequisite` is always
emitted, so a DJ never receives a silently empty result.

### R5. The colour-filter informational warning is restored (F5)

**GIVEN** a colour gate that bound an anchor meeting its prerequisites
**THEN** the informational `"{strategy} filter applied: {color}"` warning is emitted,
naming the anchor's dominant colour.

### R6. One filter serves both colour strategies (F6)

**GIVEN** `same_color` and `same_color_energy`
**THEN** the only behavioural difference between them is data on a frozen `_ColorGate`
record — `match_energy`, `reports_shortage`, and two wording fragments — consumed by a
single `_apply_color_filter` / `_color_eligible` / `_color_filter_warnings` chain.

**GIVEN** any dispatch site (recommendation, prefilter, application candidate planning,
desktop routing)
**THEN** it answers "does this strategy run the bounded colour gate?" by testing
membership in the exported `COLOR_FILTER_STRATEGIES` frozenset, never by restating the
strategy names.

### R7. No private cross-package import (F7)

**GIVEN** `desktop/main_window.py` needs a colour-anchored candidate pool
**THEN** it calls the public `plan_recommendation_candidate_context` exported from
`application.recommendation_candidates`, not a private symbol of another package.

### R8. Honest names and guarded float math (F8)

**GIVEN** the proximity helper now applied to every dominant-colour label
**THEN** it is named `_spectral_profile_close`, not `_mixed_profile_close`.

**GIVEN** a spectral feature that is NaN or infinite
**WHEN** the bounded proximity gate compares it
**THEN** `math.isfinite` guards reject it and the candidate fails closed, rather than
propagating a NaN comparison that silently reads as "not close".

## Non-functional

- No existing recommendation, candidate-pool, or desktop test may break except where a
  test pinned a deliberately-replaced contract; such tests are re-authored with a
  documented reason, never deleted.
- The change stays within the 400-line review budget.
