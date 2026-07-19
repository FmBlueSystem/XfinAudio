# Specification: Recommendation/Scoring Engine Correctness Fixes

## Requirements

### R1. Camelot wrap-around compatibility (F1)

**GIVEN** an anchor track keyed `12A` and a candidate track keyed `1A` (or any pair whose Camelot numbers wrap around 12→1)
**WHEN** `candidate_pool._camelot_compatible` evaluates the pair
**THEN** it returns `True`, matching the circular-distance logic already used by `camelot.py::_camelot_move`.

### R2. Accurate docstring for Camelot scoring (F2)

**GIVEN** `camelot.py::score_camelot_transition`'s docstring
**THEN** it describes only score values the function can actually return (no `0.7` diagonal-fuzzy claim).

### R3. Manual→generated BPM seam gate (F3)

**GIVEN** `DJControls(manual_order_paths=[...])` places one or more tracks manually, followed by generated tracks
**WHEN** the BPM jump between the last manual track and the first generated track exceeds `MAX_ADJACENT_BPM_DIFFERENCE_PERCENT` (3.0%)
**THEN** the generated track(s) are dropped the same way an internal generated→generated impossible jump already is, for both:
  - the strategy-order branch (`_uses_strategy_order` true), and
  - the optimizer branch (`recommend_sequence` path).

**GIVEN** no manual tracks are present
**THEN** behavior is unchanged from today.

### R4. Half-time/double-time BPM compatibility (F4)

**GIVEN** two tracks whose BPM ratio is within tolerance of exactly 2.0 (e.g. 128 and 64)
**WHEN** `scoring._bpm_difference_percent` computes their difference
**THEN** it returns a value near `0.0` (compatible), not ~100%.

**GIVEN** two tracks whose BPM ratio is NOT near 2.0 (e.g. 128 and 100)
**THEN** behavior is unchanged from today (plain percent-difference formula).

### R5. Cross-module BPM-formula consistency (F4 consequence, native-review CRITICAL fix)

**GIVEN** the half-time/double-time normalization added to `scoring._bpm_difference_percent` in R4
**WHEN** `quality.dj_readiness.py` validates DJ export readiness
**THEN** it uses the same `_bpm_difference_percent` logic (imported from scoring, not a local duplicate) to evaluate half-time BPM pairs as continuous/compatible.

**GIVEN** existing DJ readiness checks and export workflows
**THEN** behavior is unchanged except: half-time/double-time BPM pairs no longer falsely trigger "impossible jump" warnings during export validation.

## Non-functional

- The change must not break existing recommendation/scoring/playlist_service tests.
- Each requirement above ships with a RED-first regression test (strict TDD).
- The change must stay within the 400-line review budget.
