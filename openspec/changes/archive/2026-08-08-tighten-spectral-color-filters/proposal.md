# Proposal: Tighten Spectral Color Filters

## Intent

Make the color-based hard filters honor their guarantees. The predecessor
`tighten-same-color-energy` tightened `same_color_energy` for `MIXED` anchors
only, reasoning that RED/GREEN/BLUE "continue to require the same dominant
label" because a crossed threshold is already a real constraint. That reasoning
is empirically wrong.

`_dominant_color()` classifies by per-band threshold *excess*: RED needs
`red_ratio >= 0.45`, GREEN `>= 0.48`, BLUE `>= 0.22`, else `MIXED`. Over the
normalized simplex `r+g+b=1`, `MIXED` is a bounded triangle (L1 diameter `0.30`,
2.21% of the simplex); RED/GREEN/BLUE are unbounded above — crossing a threshold
says you passed it, not where you landed. Measured on the real 10,367-track
library, RED/GREEN/BLUE are **more** dispersed than MIXED (max pairwise L1
`0.57`–`0.71` vs MIXED `0.28`). Because MIXED is only 32% of the library, roughly
two of every three anchors take the path that was never tightened.

The maintainer's decision ("vamos con todo"): apply the real fix to both
strategies, not just correct the wording.

## Scope

### In Scope
1. **`same_color_energy`** — apply the existing bounded anchor-relative proximity
   gate (RGB L1, relative centroid, relative rolloff) to RED, GREEN and BLUE
   anchors, not only MIXED. The predicate `_same_color_energy_eligible`, the
   constants and their tests already exist; the change removes the color
   exception at `playlist_service.py:852-854`.
2. **`same_color`** — apply the same bounded proximity gate so its "Hard filter"
   description becomes true. Energy behavior is unchanged (energy stays weighted,
   not limited); only the color constraint tightens. Today `_apply_color_filter`
   admits by plain label equality (`playlist_service.py:742`), delivering
   dispersion up to `0.71` L1.
3. **Threshold naming** — the constants are named `MIXED_RGB_L1_MAX`,
   `MIXED_CENTROID_REL_MAX`, `MIXED_ROLLOFF_REL_MAX`. Once the gate applies to
   every color the `MIXED_` prefix is misleading. Rename to a color-neutral prefix
   (e.g. `COLOR_RGB_L1_MAX`) across code, tests, and the delta specs; the rule
   shape and provisional values are unchanged.
4. **Fail-closed behavior for `same_color`** — see the flagged decision below.

### HIGHEST-IMPACT DECISION — flagged for maintainer sign-off

`_apply_color_filter` currently returns the **unfiltered** pool when nothing
matches the anchor color, emitting a warning (`playlist_service.py:744-748`). A
strategy whose description says "Hard filter" silently widening to the whole
library contradicts that promise. The honest behavior mirrors
`_apply_same_color_energy_filter`: keep only preserved controls, drop every
generated candidate, and let `recommend_playlist` own the empty/short warning.
**This changes what `same_color` returns in the empty case** — an existing
strategy users rely on. This proposal recommends fail-closed for coherence, but
the maintainer may prefer to keep the current fallback. Decide before spec.

### Out of Scope (project non-goals)
- No DSP, no new audio analysis, no waveform/BPM/key detection.
- No change to `_dominant_color()` thresholds or classification.
- No schema migration, no RMS hard filter, no exact-key filtering.
- No audio mutation, no live Serato database V2 writes.
- `same_genre` shares the unfiltered-pool fallback pattern but stays unchanged
  (its equality is a genuine constraint). `same_energy`, `harmonic_journey`,
  `warmup`, `build`, `peak_time`, `chill`, `same_vibe` are unchanged.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `same-color-energy-strategy`: extend the bounded proximity gate to
  RED/GREEN/BLUE anchors; rename the color-neutral thresholds.
- `same-color-strategy`: replace plain label equality with the bounded proximity
  gate; resolve the empty-pool fallback per the flagged decision.

## Approach

Reuse the shipped, tested gate `_mixed_profile_close` — it already computes RGB
L1, relative centroid, and relative rolloff against the anchor and fails closed
on degenerate values. For `same_color_energy`, delete the
`dominant_color != "MIXED"` early return so every color passes label equality
**and** the bounded gate. For `same_color`, replace the label-equality list
comprehension in `_apply_color_filter` with the same gate against a bound anchor
profile (energy stays out of it). Rename the `MIXED_*` constants to a
color-neutral prefix. The rule shape is fixed; the literal magnitudes remain
PROVISIONAL pending listening calibration and stay isolated so a post-calibration
change touches only the constant definitions.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/xfinaudio/recommendation/playlist_service.py` | Modified | Remove the MIXED-only exception in `_same_color_energy_eligible`; apply the gate in `_apply_color_filter`; rename constants; resolve `same_color` fallback. |
| `src/xfinaudio/recommendation/strategies.py` | Modified | Tighten `same_color` description to a true hard filter (color-bounded); confirm `same_color_energy` wording. |
| `tests/test_playlist_service.py` | Modified | Strict-TDD boundaries for RED/GREEN/BLUE gate, `same_color` gate, fallback, constant renames. |
| `openspec/specs/same-color-energy-strategy/spec.md` | Modified | Extend gate to all colors; rename thresholds. |
| `openspec/specs/same-color-strategy/spec.md` | New/Modified | Bounded color gate and empty-pool contract. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Tightening RED/GREEN/BLUE shrinks those pools substantially | High | Forecast the magnitude per color at busy energy levels during spec/calibration; shorter honest sets are the intended tradeoff. |
| `same_color` results change for existing users | High | Flag the fallback decision for maintainer sign-off before spec; document the behavior change. |
| Constants stay calibration-provisional; extending to three colors widens calibration surface | Medium | Keep constants isolated and color-neutral; recalibration touches only definitions. |

## Rollback Plan

Revert together: the removed MIXED exception, the `_apply_color_filter` gate, the
constant renames, the `same_color` fallback change, the strategy descriptions,
the tests, and the delta specs. Restore prior label equality and fallback. No
stored spectral profiles change, so rollback needs no data migration.

## Dependencies

- Existing cached spectral profiles and a read-only real-library database copy
  for calibration and per-color pool forecasting.

## Implementation Envelope

Estimated within the 400-line review budget: the core change removes a color
exception, redirects one filter to an existing helper, and renames constants,
plus their tests and delta specs. If per-color test coverage and both delta
specs push past 400 changed lines, declare chained PRs at the tasks phase
(slice A: `same_color_energy` + rename; slice B: `same_color` + fallback).

## Success Criteria

- [ ] Every generated `same_color_energy` candidate passes the bounded gate for
      its anchor color (RED/GREEN/BLUE and MIXED), not label equality alone.
- [ ] `same_color` admits only tracks inside the bounded color gate; its
      description matches its behavior.
- [ ] The empty-pool case for `same_color` behaves per the maintainer's signed-off
      decision (fail-closed recommended) — never a silent unfiltered widen unless
      explicitly retained.
- [ ] Thresholds are color-neutral in name and applied identically across colors.
- [ ] `same_energy`, `same_genre`, controls, and Camelot behavior unchanged.
- [ ] Per-color pool shrinkage is forecast and documented before implementation.
