# Proposal: Quality readiness required fields

## Intent

Make DJ readiness validate required metadata from the actual track fields, not only from `metadata_status` or `missing_required_fields`. A track marked complete but missing BPM, Camelot key, or energy should still block live/export readiness.

## Scope

In scope:
- Add a focused DJ readiness regression test for missing required fields on a complete track.
- Update the pure quality readiness metadata check to inspect `bpm`, `camelot_key`, and `energy_level` directly.
- Preserve existing ready/review/block semantics.

Out of scope:
- Changing recommendation scoring, export formats, UI copy, DSP, audio mutation, or Serato DB V2 writes.
