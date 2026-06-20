# Serato Export Application Boundary

Move recommendation Serato crate preview/export behind an application use case so desktop keeps only gate checks, UI copy, readiness sidecars, and history rendering.

In scope: application preview/export service, injected writer/discoverer seams, desktop delegation, tests, SDD evidence.
Out of scope: metadata worklist export refactor, DSP/audio mutation, live Serato DB V2 writes.

Success: desktop no longer performs recommendation Serato planning/writing directly; Serato behavior and safety remain unchanged; full gates pass.
Rollback: revert the use case and restore the previous coordinator calls.
