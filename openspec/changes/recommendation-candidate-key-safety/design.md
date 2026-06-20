# Design: Recommendation candidate key safety

## Approach

Keep the policy inside `xfinaudio.recommendation.candidate_pool`, because this module owns the pure interactive-size pool ranking used by desktop adapters. Add a small parse helper around Camelot keys and let invalid keys fall into the same bucket as missing/unknown keys.

## Safety

This does not change final transition scoring, export behavior, Serato writes, audio files, or DSP. It only prevents candidate-pool preselection from crashing on malformed metadata.
