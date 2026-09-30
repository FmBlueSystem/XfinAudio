# Apply progress

## 2026-09-30 — snapshot regression contract

- Recovered the in-progress migration and verified its original RED transcript: all four `test_state_snapshot_contract.py` cases failed against the mutable implementation (direct assignment and unknown keys were accepted; shell writes and runtime refresh changed old snapshots).
- RED command: `QT_QPA_PLATFORM=offscreen uv run pytest -q tests/test_state_snapshot_contract.py` (4 failed, recorded before production edits).
- The regression slice captures field immutability, checked field names, scan/shell publication to controller owners, and selection snapshot preservation.
- Kept unrelated completion batching, audio, DSP, export and lifecycle work untouched.

Implementation and verification evidence follows in the next chained slices.
