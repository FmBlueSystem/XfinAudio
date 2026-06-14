# Apply Progress: No Unsafe Live Serato Writes

## Summary

All planned tasks were applied. The Export screen now clearly communicates that live Serato library writes are not part of the verified release candidate. The release notes template reinforces the same boundary. Tests lock in the warning text.

## Key decisions

- Kept Serato export functionality enabled; only the user-facing copy and documentation were changed.
- Used stable key phrases in tests rather than full sentences to reduce brittleness.
- Did not modify translation files; English source strings remain the RC source of truth.

## Files changed

- `src/xfinaudio/desktop/export_view_model.py`
- `src/xfinaudio/desktop/screens/export_screen.py`
- `docs/release-notes-template.md`
- `tests/test_export_view_model.py`
- `tests/test_export_screen_copy.py`
