# Proposal: Same Color & Energy Strategy

## Intent

A DJ who wants a set that stays timbrally cohesive AND energetically flat has no
single strategy that enforces both as hard constraints. Today the two intents
live in separate profiles: `same_energy` enforces a hard ±1 energy band
(`energy_tolerance=1`) but is color-blind, while `same_color` enforces a hard
anchor-color prefilter but only soft-weights energy at 0.20. Choosing one
silently abandons the other constraint, so the DJ must hand-prune results to get
a same-color, same-energy pool.

This change adds a new strategy profile, `same_color_energy` ("Same Color &
Energy"), that composes the existing hard anchor-color filter with a hard
`energy_tolerance=1` energy band. Success looks like: selecting the new strategy
produces a playlist where every non-control candidate shares the anchor's
dominant spectral color and sits within ±1 of the anchor energy, using only the
two generic mechanisms already in place, with all existing strategies unchanged.

## Proposal Question Round

Interactive questions were skipped: scope, name, and mechanism are fully
pre-decided with the user. This is an additive change — `same_color` semantics
must not change. Assumptions carried into spec/design:

- New profile only; no edits to `same_color` or `same_energy` behavior.
- Both mechanisms already generalize: `_apply_energy_tolerance` keys off
  `strategy.energy_tolerance`; the color filter is dispatched by name equality.
- Suggested weights (harmonic 0.25, bpm 0.15, energy 0.30, tags 0.10, spectral
  0.20) are a starting point; the exact values settle in design.
- Fallback on an empty pool must match the existing `same_color` fallback (fall
  back to unfiltered scoring, emit a warning) rather than error.

## Scope

### In Scope
- New `_STRATEGIES["same_color_energy"]` entry plus the `StrategyName` Literal
  extension, with `energy_tolerance=1` and spectral-aware weights.
- Widen the color-filter dispatch from `strategy.name == "same_color"` to
  membership in a color-strategy set at both call sites
  (`playlist_service.py:162` and `:392`).
- Decide and apply warning-message compatibility (energy tolerance warning
  hardcodes `same_energy`; color warnings hardcode `same_color`) — settle
  whether messages become strategy-name-aware in design.
- Strict-TDD coverage: profile registration, hard color AND hard energy band
  both enforced, empty-pool fallback, and UI dropdown pickup.
- Guarantee-explicit strategy descriptions (user feedback 2026-07-19: the UI
  description line must state what is a hard constraint vs a weighted
  preference). Ship the new profile with an explicit description and sharpen
  the `same_energy` and `same_color` descriptions to state their actual
  guarantees. Copy-only; no behavior change.

### Out of Scope
- Changing `same_color`, `same_energy`, or any existing strategy semantics
  (their `description` copy is explicitly in scope above; filtering, scoring,
  and warning behavior are not).
- UI redesign, scoring-engine changes, spectral-analyzer changes.
- New color or energy heuristics beyond composing the two existing filters.

## Capabilities

### New Capabilities
- `same-color-energy-strategy`: a playlist strategy that enforces the anchor's
  dominant spectral color and a ±1 energy band as combined hard constraints,
  with graceful fallback when no candidates match.

### Modified Capabilities
- None. Existing strategy behavior is preserved; this is purely additive.

## Approach

Follow RED → GREEN → REFACTOR → VERIFY.

1. Register `same_color_energy` in `_STRATEGIES` and the `StrategyName` Literal.
   `_apply_energy_tolerance` already keys off `energy_tolerance`, so the energy
   band activates with no dispatch change.
2. Replace both `strategy.name == "same_color"` checks with membership in a
   single color-strategy name set (or equivalent minimal seam) so the anchor
   color filter runs for both profiles at the recommend and candidate-cap sites.
3. Decide warning-message strategy-name awareness; keep messages coherent with
   the active strategy without breaking existing `same_color`/`same_energy`
   wording.
4. Verify the UI strategy dropdown enumerates the profile automatically via
   `list_strategy_catalog()` / `available_strategies()`; add no bespoke wiring
   if it does.

Expected to fit the 400-line review budget as a single slice.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/xfinaudio/recommendation/strategies.py` | Modified | New `_STRATEGIES` entry; extend `StrategyName` Literal |
| `src/xfinaudio/recommendation/playlist_service.py` | Modified | Widen color-filter dispatch at `:162` and `:392`; warning-message compatibility |
| `tests/test_playlist_strategies.py` (and related) | Modified | RED tests for registration, dual hard constraints, fallback, UI pickup |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Widening name dispatch alters `same_color` behavior | Low | Use a set containing both names; assert `same_color` output unchanged in tests |
| Hardcoded `same_energy`/`same_color` warning text becomes misleading | Medium | Settle name-aware messaging in design; assert wording in tests |
| Combined hard filters over-prune to an empty pool | Medium | Reuse existing `same_color` fallback-to-unfiltered path; cover with a test |
| New name missing from `StrategyName` Literal breaks typing | Low | Extend Literal in the same change; `pyright` guards regressions |

## Rollback Plan

Revert the change. The new profile is additive and name-scoped, so removing the
`_STRATEGIES` entry, the Literal member, and the widened dispatch restores prior
behavior with no persisted-data or existing-strategy impact.

## Dependencies

- Existing `uv`, pytest, Pyright, Ruff, and release gate. No new runtime deps.

## Success Criteria

- [ ] Selecting `same_color_energy` yields candidates that all share the anchor
      dominant color AND fall within ±1 of anchor energy (control paths aside).
- [ ] `same_color` and `same_energy` behavior is provably unchanged.
- [ ] Empty-pool fallback matches the existing `same_color` fallback.
- [ ] The strategy appears in the UI strategy dropdown automatically.
- [ ] Full verification and the release gate pass.
