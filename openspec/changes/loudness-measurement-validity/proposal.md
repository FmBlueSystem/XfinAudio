# Loudness validity correction

Reject startup LRA and undefined/nonfinite results without changing the measurement engine or normal-song workflow. Independent production tests reproduced LRA 20 LU on constant 3.0–3.3 s tones, and false integrated -70 LUFS below the absolute gate.

Scope: partial measurement validity, tag/cache versioning, focused display qualification and synthetic regressions. No user audio, real tag writes, new DSP implementation or dependency. Preserve automatic loudness comments for complete current measurements. Rollback requires reverting the source and version together.

Chained commits under 400 changed lines: domain/cache/tag correction; numerical regressions and bounded display wording. Full integrated release gate remains coordinator-owned.
