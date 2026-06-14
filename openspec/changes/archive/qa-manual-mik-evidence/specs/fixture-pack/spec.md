# Spec: Mixed In Key Fixture Pack

## Goal

Expand automated test fixtures with MIK-style metadata variants so the scan/recommend/export pipeline is exercised against realistic edge cases without requiring the maintainer's private library in every CI run.

## Acceptance Criteria

- New fixture file `tests/fixtures/mik_processed/tag_variants.json` exists.
- It contains at least these cases:
  - `complete`: all required fields (BPM, Camelot key, energy).
  - `incomplete_missing_key`: BPM and energy present, key absent.
  - `incomplete_missing_energy`: BPM and key present, energy absent.
  - `incomplete_missing_bpm`: key and energy present, BPM absent.
  - `conflicting_energy_json_vs_text`: JSON energy says 7, `energylevel` text says 6.
  - `bpm_fallback_tbpm`: `bpm` invalid, `tbpm` valid.
- New tests load these fixtures and assert correct `metadata_status`, `bpm`, `camelot_key`, and `energy_level`.
- Optional: helper function in `tests/` to write these tags into a copied WAV fixture for real-scan tests.
