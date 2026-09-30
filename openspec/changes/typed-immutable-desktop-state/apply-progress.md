# Apply progress

## 2026-09-30 — snapshot regression contract

- Recovered the in-progress migration and verified its original RED transcript: all four `test_state_snapshot_contract.py` cases failed against the mutable implementation (direct assignment and unknown keys were accepted; shell writes and runtime refresh changed old snapshots).
- RED command: `QT_QPA_PLATFORM=offscreen uv run pytest -q tests/test_state_snapshot_contract.py` (4 failed, recorded before production edits).
- The regression slice captures field immutability, checked field names, scan/shell publication to controller owners, and selection snapshot preservation.
- Kept unrelated completion batching, audio, DSP, export and lifecycle work untouched.

Implementation and verification evidence follows in the next chained slices.

## Replacement publication implementation

- Froze AppState fields; `model_copy` uses `dataclasses.replace` and rejects unknown field names without publishing a partial update.
- Converted helper methods, scan start/progress/finish, runtime refresh and legacy shell writes to replacement snapshots. Legacy token reads are side-effect free.
- Added narrow typed current-state/publication callbacks and corrected screen literals to include existing playlists/live screens. Updated fixture setup to use supported replacements.
- GREEN: the original 4 snapshot contracts and the full 190-test state/scan/view-model subset pass after recovery. The final validation slice adds standalone accessor/type contracts and broader gate evidence.
