# Proposal: Recommendation candidate key safety

## Intent

Make the pure recommendation candidate pool resilient when a complete track contains an invalid Camelot key. Pool building should rank such tracks as key-unknown/incompatible instead of crashing before the recommendation workflow can continue.

## Scope

In scope:
- Add focused tests around invalid Camelot keys in `build_recommendation_pool()`.
- Update candidate-pool key compatibility policy to treat invalid keys as not compatible.
- Preserve existing candidate ordering behavior for valid keys.

Out of scope:
- Changing Camelot scoring rules used by final transition scoring.
- Changing export formats, Serato DB V2 behavior, audio analysis, or UI behavior.
- Adding DSP or mutating audio files.
