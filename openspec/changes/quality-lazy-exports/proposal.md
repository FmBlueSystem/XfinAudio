# Change: quality-lazy-exports

## Intent
Stop package-level `xfinaudio.quality` imports from eagerly loading readiness/export infrastructure when callers only need pure recommendation quality reporting.

## Scope
- Make `xfinaudio.quality` public exports lazy while preserving the existing API.
- Add regression coverage for isolated pure quality imports.
- Keep all changes inside package export boundaries and tests.

## Out of scope
- Recommendation algorithm changes.
- Desktop/UI changes.
- Export format changes.
- Audio mutation, DSP, or live Serato DB V2 writes.

## Success criteria
- Importing `xfinaudio.quality.recommendation_quality` does not load `xfinaudio.quality.dj_readiness`.
- Existing `from xfinaudio.quality import ...` public imports still work.
- Full verification gates pass.
