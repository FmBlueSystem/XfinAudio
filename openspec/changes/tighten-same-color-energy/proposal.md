# Proposal: Tighten Same Color & Energy

## Intent

Make `same_color_energy` honor its guarantee. Playlist 43 showed that label equality plus an anchor-relative +/-1 energy band admits audibly different tracks, especially inside the broad `MIXED` bucket.

## Scope

### In Scope
- Require exact anchor energy for generated candidates under `same_color_energy`.
- For a `MIXED` anchor, require proximity using cached RGB ratios, centroid, and rolloff; retain label matching for RED/GREEN/BLUE.
- Apply combined eligibility before candidate-pool capping and fail closed when anchor metadata is missing or no eligible candidates remain.
- Preserve control tracks and emit explicit empty/short-pool warnings.
- Calibrate proposed thresholds through real-library, offscreen, and listening checks.

### Out of Scope
- Changes to `same_color` or `same_energy` behavior.
- Exact Camelot-key matching or changes to harmonic scoring.
- New audio analysis, DSP, schema migrations, or RMS hard filtering.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `same-color-energy-strategy`: tighten candidate membership, prerequisites, and fallback while preserving existing strategies.

## Approach

Use a strategy-specific combined predicate before pool capping. Require candidate energy to equal anchor energy. For `MIXED`, require a bounded anchor-relative proximity gate over RGB L1 distance, relative centroid, and relative rolloff, expressed as calibration-provisional named constants `MIXED_RGB_L1_MAX` (initial `0.08`), `MIXED_CENTROID_REL_MAX` (initial `0.15`), and `MIXED_ROLLOFF_REL_MAX` (initial `0.15`). The rule shape (label equality plus the bounded gate) is fixed; the literal numeric values are PROVISIONAL pending listening calibration, so a post-calibration change touches only the constant definitions across proposal, design, spec, and tests. The bounded gate is required regardless of calibration because `MIXED` is a broad residual bucket (the ELSE of three independent thresholds, L1 diameter 0.30) where label equality alone constrains nothing. Keep Camelot independent. Never widen strict results to unfiltered candidates; preserve user-controlled tracks and report missing prerequisites or insufficient supply.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/xfinaudio/recommendation/strategies.py` | Modified | Exact-energy strategy contract and description. |
| `src/xfinaudio/recommendation/playlist_service.py` | Modified | Atomic strict eligibility and fail-closed warnings. |
| `src/xfinaudio/audio/spectral_profile.py` | Modified | Pure anchor-relative distance support if shared. |
| `tests/` | Modified | Strict-TDD boundaries, regressions, and fallback coverage. |
| `openspec/specs/same-color-energy-strategy/spec.md` | Modified | Durable behavioral requirements. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Thresholds overfit one anchor | Medium | Calibrate across colors and multiple real-library anchors. |
| Sparse libraries yield short results | Medium | Fail honestly and warn instead of violating the guarantee. |
| Compatibility regression | Low | Characterize `same_color`, `same_energy`, controls, and Camelot first. |

## Rollback Plan

Revert the strategy-specific predicate, constants, warnings, tests, and delta spec together; restore the prior +/-1 and fallback contract without changing stored profiles.

## Dependencies

- Existing cached spectral profiles and real-library database copy for read-only calibration.

## Success Criteria

- [ ] Every generated candidate has exact anchor energy and satisfies the applicable spectral rule.
- [ ] Missing data and empty/short pools never trigger silent unfiltered fallback.
- [ ] `same_color`, `same_energy`, controls, and Camelot behavior remain unchanged.
- [ ] Boundary tests and real-library offscreen/listening calibration support the chosen thresholds.
