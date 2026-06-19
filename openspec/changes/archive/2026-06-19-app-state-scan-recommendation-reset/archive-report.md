# Archive Report: AppState scan recommendation reset boundary

## Result

Archived after implementation and verification.

## Summary

- Added `apply_scan_context_reset()` as a pure AppState transition helper.
- Updated `LibraryController.clear_scan_dependent_state()` to delegate reset policy to the helper.
- Added focused unit coverage for immutable reset behavior.
- Updated durable `desktop-main-window` specification with the scan context reset boundary.

## Verification

- Focused tests: PASS.
- `uv run pyright src tests`: PASS.
- `uv run python scripts/release_gate_check.py --run`: PASS, 886 tests, total coverage 90.16%.

## Safety

No audio mutation, DSP expansion, or Serato DB V2 writes.
