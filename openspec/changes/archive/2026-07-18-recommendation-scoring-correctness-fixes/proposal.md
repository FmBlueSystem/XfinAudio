# Proposal: Recommendation/Scoring Engine Correctness Fixes

## Intent

Fix four correctness issues in `src/xfinaudio/recommendation/` found via a Claude+Codex adversarial review (`/grill-me-codex`, see `PLAN.md` / `PLAN-REVIEW-LOG.md` at repo root for the full grill/review transcript). Two are confirmed logic bugs; two are design gaps resolved with explicit product decisions.

## Scope

### In scope

- F1: `candidate_pool.py::_camelot_compatible` does not handle Camelot wheel wrap-around (12↔1 treated as incompatible).
- F2: `camelot.py::score_camelot_transition` docstring promises a `0.7` "diagonal fuzzy" score the function never returns.
- F3: `playlist_service.py`'s impossible-BPM-jump gate does not apply to the seam between the last manually-ordered track and the first generated track.
- F4: `scoring.py::_bpm_difference_percent` scores exact half-time/double-time BPM pairs (e.g. 128 vs 64) as ~100% incompatible instead of recognizing the 2:1 relationship.

### Out of scope

- `audio/` (spectral analysis) and `quality/` (DJ readiness scoring) clusters.
- Performance/complexity improvements and harmonic-mixing heuristic quality beyond the four items above.
- Any refactor of `_drop_generated_tracks_after_impossible_bpm_jumps` internals — only its call sites change (F3).

## Success criteria

1. `12A`/`1A` (and any wrap-around pair) score as Camelot-compatible in `candidate_pool.py`, matching `camelot.py`'s existing wrap-around logic.
2. `score_camelot_transition`'s docstring accurately describes its own branches.
3. A BPM jump >3% between the last manual track and the first generated track drops generated tracks the same way a generated→generated jump already does, for both the strategy-order and optimizer sequencing branches.
4. BPM pairs in an exact 2:1 ratio (within tolerance) score as compatible instead of ~0% compatible.
5. All verification commands pass.
6. No audio files are mutated; no live Serato database V2 writes.

## Rollback plan

Each fix is an isolated function-level change with dedicated regression tests; revert per-fix if a regression surfaces.

## Review budget

Estimated changed lines: ~40 production + ~120 test lines, well within the 400-line budget.
