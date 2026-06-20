# Design: quality-manual-overlap

## Architecture impact
This is a pure quality-domain change. It stays inside `src/xfinaudio/quality/recommendation_quality.py` and its unit tests.

## Current behavior
`_overlap_ratio()` computes intersection with sets but divides by the original `manual_paths` length. Duplicate manual paths are removed from the numerator but still counted in the denominator.

## Proposed behavior
Normalize manual paths to a set once, use that same distinct set for both numerator and denominator, and keep the empty-list guard.

## Safety
- No UI changes.
- No audio mutation.
- No DSP.
- No Serato DB V2 writes.
- No dependency changes.
