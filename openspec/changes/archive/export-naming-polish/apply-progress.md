# Apply Progress: Export Naming Polish

## Summary

All planned tasks were applied. Non-Serato DJ software exports now use descriptive, timestamped, filesystem-safe default filenames instead of the static `"XfinAudio Export"` fallback.

## Key decisions

- Created a dedicated `export_naming.py` utility so naming logic is reusable and testable.
- Kept Serato crate naming unchanged; it already includes timestamp and strategy.
- Used lowercase sanitized output for filesystem safety across platforms.
- Preserved explicit `crate_name` and Prep Copilot variant overrides.

## Files changed

- `src/xfinaudio/exporting/export_naming.py`
- `src/xfinaudio/desktop/export_coordinator.py`
- `tests/test_export_naming.py`
