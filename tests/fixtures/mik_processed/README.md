# Mixed In Key Test Fixtures

This directory contains MIK-style metadata fixtures used by XfinAudio tests.

## Files

- `tag_variants.json` — Metadata dictionaries covering complete, incomplete, conflicting, and fallback cases.
- `silence_1s.wav` — Committed one-second silence WAV (stored in the parent `tests/fixtures/` directory).

## Using fixtures in tests

For pure parser tests, load `tag_variants.json` and pass the dictionary directly to `parse_mixedinkey_tags`.

For real-scan integration tests, use the helper in `tests/test_smoke_real_audio_scan_recommend_export.py` or a similar helper to copy `silence_1s.wav` and write the tags via mutagen.

## Cases covered

| Case | Expected status | Notes |
|------|-----------------|-------|
| `complete` | complete | All required fields present. |
| `incomplete_missing_key` | incomplete | BPM and energy present, key absent. |
| `incomplete_missing_energy` | incomplete | BPM and key present, energy absent. |
| `incomplete_missing_bpm` | incomplete | Key and energy present, BPM absent. |
| `conflicting_energy_json_vs_text` | complete | JSON `energy` should win over `energylevel`. |
| `bpm_fallback_tbpm` | complete | Invalid `bpm` falls back to `tbpm`. |
| `lowercase_variant` | complete | Lowercase tag variants (`tbpm`, `tkey`) are accepted. |
