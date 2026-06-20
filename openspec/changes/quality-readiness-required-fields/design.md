# Design: Quality readiness required fields

## Approach

Keep the rule in `xfinaudio.quality.dj_readiness`, because readiness owns final operational go/no-go checks. Extend `_metadata_check()` to identify tracks with absent `bpm`, `camelot_key`, or `energy_level` in addition to incomplete status and explicit `missing_required_fields`.

## Safety

This is a pure quality gate. It does not alter audio analysis, DSP, Serato writes, export formats, or UI behavior.
