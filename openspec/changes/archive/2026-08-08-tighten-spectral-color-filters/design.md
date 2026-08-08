# Design: Tighten Spectral Color Filters

## Technical Approach

Two moves in `src/xfinaudio/recommendation/playlist_service.py`. (1) Extend the
already-shipped bounded proximity gate from MIXED-only to every dominant-color
label by deleting one early return in `_same_color_energy_eligible`, then rename
the three `MIXED_*` constants to a colour-neutral prefix. (2) Give `same_color`
the same bounded colour gate and make it fail closed — via a NEW dedicated
`_apply_same_color_filter` modelled on the shipped `_apply_same_color_energy_filter`,
leaving the shared `_apply_color_filter` (still used by nothing else after the
cut) and `_apply_genre_filter` byte-compatible. Energy stays out of the
`same_color` path entirely — no `_apply_energy_tolerance`, no exact-energy check.
The gate helper `_mixed_profile_close` (line 810), `_relative_delta` (line 798),
and the finite/positive guards (lines 790-795) are reused verbatim; only their
constant references get renamed.

## Architecture Decisions

| Decision | Alternative | Rationale |
|---|---|---|
| Delete the `anchor_profile.dominant_color != "MIXED"` early return at `playlist_service.py:852-853` | Add per-colour constant sets | The gate is already colour-agnostic below that line; removing the exception is the whole behavior change. One deletion, not a rewrite. |
| Rename `MIXED_RGB_L1_MAX`/`MIXED_CENTROID_REL_MAX`/`MIXED_ROLLOFF_REL_MAX` (lines 58-60) to `COLOR_RGB_L1_MAX`/`COLOR_CENTROID_REL_MAX`/`COLOR_ROLLOFF_REL_MAX` | Keep names, add alias | The `MIXED_` prefix is a lie once the gate spans all colours; a lingering alias invites drift. Values (`0.08`, `0.15`, `0.15`) unchanged. |
| Give `same_color` its OWN `_apply_same_color_filter`, mirroring `_apply_same_color_energy_filter` | Route `same_color` through a shared bounded-gate helper reused by both strategies | A shared helper would tempt coupling `same_color` to the energy path's exact-energy check. A dedicated colour-only filter makes "colour gate, no energy limit" structurally impossible to violate. Tradeoff: ~1 helper + 1 warnings function of near-duplicate shape; accepted for isolation. |
| `same_color` fails closed by NOT using `_apply_color_filter`'s unfiltered fallback | Edit `_apply_color_filter` to fail closed | `_apply_color_filter` shares its warning/fallback SHAPE with `_apply_genre_filter` (line 616), and `same_genre`'s equality fallback is explicitly out of scope. Editing the shared helper risks `same_genre`. A dedicated helper touches neither. |
| Introduce a colour-only eligibility predicate `_same_color_eligible(anchor, candidate)` | Reuse `_same_color_energy_eligible` with energy skipped | `_same_color_energy_eligible` (line 834) enforces exact energy at line 848; `same_color` must not. A sibling predicate = label equality + `_mixed_profile_close`, no energy branch. |

## Data Flow

```text
same_color_energy (unchanged flow, gate now spans all colours):
  ... -> _apply_same_color_energy_filter -> _same_color_energy_eligible
       -> (label + energy) AND _mixed_profile_close  # for EVERY colour now

same_color (new):
  full library -> complete -> shared strategy/range -> requested genre
    -> _resolve_anchor_color / bind anchor track
    -> _apply_same_color_filter (colour gate, controls preserved, fails closed)
    -> recommend_playlist owns empty/shortage warning
    -> weighted scoring (energy still a weight, never a filter)
```

`recommend_playlist` (dispatch at lines 265-297) replaces the
`strategy.name in _COLOR_FILTER_STRATEGIES` branch (line 265) for `same_color`
with a `_apply_same_color_filter` + `_same_color_warnings` block shaped like the
`same_color_energy` block at lines 270-297, minus energy/anchor-path transport.
`prefilter_strategy_candidates` (line 691) gets the mirrored change. No desktop
service-wiring seam is needed: `same_color` binds no immutable anchor path and
takes no context callback, so unlike the predecessor there is no
`RecommendationService`/`window_service_wiring` change. Verified: `same_color`
today flows only through the two `_COLOR_FILTER_STRATEGIES` call sites (lines
265, 691).

## File Changes

| File | Action | Description |
|---|---|---|
| `src/xfinaudio/recommendation/playlist_service.py` | Modify | Delete `!= "MIXED"` early return (852-853); rename 3 constants + all refs (58-60, 824, 828, 831); add `_same_color_eligible`, `_apply_same_color_filter`, `_same_color_warnings`; rewire `same_color` dispatch (265-269 and 691-694) off `_apply_color_filter`; drop `same_color` from `_COLOR_FILTER_STRATEGIES` (46). |
| `src/xfinaudio/recommendation/strategies.py` | Modify | `same_color` description (102-103) already claims "Hard filter … Energy is weighted but not limited" — keep; confirm `same_color_energy` (116). Likely zero-line change; verify wording matches new behavior. |
| `tests/test_playlist_service.py` | Modify | Rename constant refs; replace the two characterization tests (see Testing Strategy); add RED/GREEN/BLUE gate tests for both strategies; add `same_color` fail-closed + energy-still-weighted + controls-preserved tests. |
| `openspec/specs/same-color-energy-strategy/spec.md` | Modify | Extend gate to all colours; colour-neutral constant names (delta already written). |
| `openspec/specs/same-color-strategy/spec.md` | Modify/New | Bounded colour gate + fail-closed contract (delta already written). |

Constant rename also reaches predecessor artifacts that named `MIXED_*`:
`openspec/changes/tighten-same-color-energy/design.md` (lines 47, 92) and any
predecessor test referencing the old names. The rename must move coherently or
`ruff`/`pyright` and the predecessor's own tests break.

## Interfaces / Contracts

`_same_color_eligible(anchor: TrackRecord, candidate: TrackRecord) -> bool`:
label equality against the bound anchor AND `_mixed_profile_close(anchor_profile,
candidate_profile)`; fails closed on missing profiles. NO energy comparison.
`_apply_same_color_filter(...)` mirrors `_apply_same_color_energy_filter`
(907-945): preserved controls always survive; non-controls survive only on
`_same_color_eligible`; warningless. `_same_color_warnings(...)` mirrors
`_same_color_energy_warnings` (1021-1064) minus the energy phrasing and the
exact-energy shortage semantics: it emits the prerequisite-missing and
strict-empty warnings so the pool never widens.

## Pool Impact Forecast

Baseline (busiest energy level per anchor colour, shipped predicate = label +
exact energy, gate applied to MIXED only):

| Anchor | Admitted today | Max L1 today | After gate (`COLOR_RGB_L1_MAX=0.08`) |
|---|---|---|---|
| RED | 438 | 0.4127 | sharp drop — 0.08 is ~5x tighter than 0.41 |
| GREEN | 2295 | 0.4523 | sharp drop |
| BLUE | 796 | 0.3688 | sharp drop |
| MIXED | 466 | 0.0799 | ~unchanged (already gated; 0.0799 ≤ 0.08) |

RED/GREEN/BLUE pools shrink substantially — the intended tradeoff. The
implementation surfaces shortage HONESTLY, never by widening: `_same_color_warnings`
emits the strict-empty warning and returns only preserved controls, and the
shortage warning when eligible < requested. This is the same fail-closed contract
`same_color_energy` already ships (`_same_color_energy_warnings`, 1050-1063).
Exact post-gate counts are a calibration acceptance-gate measurement (scratch DB,
offscreen `MainWindow`), not a design blocker; the constants stay isolated so
recalibration touches only lines 58-60.

## Testing Strategy

**Characterization exception — declared, not assumed.** The standing rule is a
characterization test is NEVER edited to accommodate new code. The ONLY legitimate
exception is when it pins the exact behavior being deliberately changed. That
exception applies here and is declared explicitly:
`test_apply_color_filter_same_color_falls_back_to_unfiltered_pool`
(`tests/test_playlist_service.py:1369`) pins `filtered is candidates` (unfiltered
widen) + the two exact warning strings — the behavior this change replaces with
fail-closed. `test_apply_color_filter_same_color_keeps_matching_candidates`
(line 1392) pins plain label equality (`{/anchor.flac, /red2.flac}`) — replaced
by the bounded gate. Both MUST change; both target the deliberately-replaced
behavior. They are re-authored (not deleted) as fail-closed / bounded-gate tests
for the new `_apply_same_color_filter`.

**Byte-compatibility net (proves out-of-scope strategies unchanged).**
`same_genre` via `_apply_genre_filter` (616) — its unfiltered-fallback
characterization and warning strings (623-630) MUST stay green untouched, proving
the shared-shape helper was not disturbed. `same_energy` `±1` band, plus
`harmonic_journey`, `warmup`, `build`, `peak_time`, `chill`, `same_vibe` — the
predecessor's characterization tests pinning ordered candidates + warnings MUST
stay green, proving byte-compatibility. Name these in the verify report.

**Strict TDD (RED first).** Per colour (RED/GREEN/BLUE/MIXED) for BOTH
`same_color` and `same_color_energy`: same-label candidate inside the gate
admitted; outside `COLOR_RGB_L1_MAX` rejected; exactly at each bound eligible
(inclusive); degenerate profile / zero denominator fails closed. `same_color`
only: candidate outside anchor energy still eligible (energy weighted, not
limited); empty strict pool returns controls-only + warning, never the unfiltered
library; controls preserved through the gate. Constant-rename: assert no
`MIXED_`-prefixed gate constant remains.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable
classification, or process boundary.

## Implementation Envelope

Within the 400-line review budget. Slice A (`same_color_energy` exception removal
+ constant rename + coherent ref moves): small, mostly a deletion and mechanical
rename. Slice B (`same_color` dedicated filter + fail-closed + gate + tests): the
bulk, ~1 predicate + 1 filter + 1 warnings helper (each near-clone of a shipped
sibling) plus per-colour tests. If per-colour coverage for two strategies plus
both delta specs pushes past 400 changed lines, declare chained PRs at the tasks
phase (A then B); the split is already clean along strategy lines.

## Migration / Rollout

No schema migration, no DSP, no new audio analysis, no `_dominant_color()`
change, no RMS/exact-key filter, no audio mutation, no Serato V2 writes. Stored
spectral profiles are untouched, so rollback needs no data migration — revert
the deletion, the rename, and the `same_color` block together.

## Open Questions

- **Fail-closed sign-off.** The proposal flags the `same_color` empty-case
  behavior change (unfiltered widen → controls-only) for maintainer sign-off.
  The delta spec (`same-color-strategy/spec.md`) already commits to fail-closed;
  this design assumes that sign-off is granted. If the maintainer prefers to
  retain the unfiltered fallback, the `_apply_same_color_filter` empty branch and
  its warnings change accordingly — a scoped, isolated edit.
- **Provisional constants.** `COLOR_RGB_L1_MAX`/`COLOR_CENTROID_REL_MAX`/
  `COLOR_ROLLOFF_REL_MAX` (`0.08`/`0.15`/`0.15`) require listening calibration
  across RED/GREEN/BLUE/MIXED anchors AFTER implementation. Acceptance gate, not
  a design blocker; the rule shape is normative and the constants are isolated.
