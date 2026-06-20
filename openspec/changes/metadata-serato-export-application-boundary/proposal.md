# Metadata Serato Export Application Boundary

Move metadata worklist Serato crate export planning/writing behind an application use case so desktop remains a UI adapter.

In scope: status and missing-field metadata worklist export use cases, injected writer/discoverer seams, desktop delegation, tests, SDD evidence.
Out of scope: recommendation Serato export, DSP/audio mutation, live Serato DB V2 writes.

Success: desktop no longer plans/writes metadata worklist Serato crates directly; behavior and safety remain unchanged; full gates pass.
