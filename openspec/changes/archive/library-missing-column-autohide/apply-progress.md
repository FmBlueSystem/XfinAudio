# Apply Progress: Auto-hide Missing Column in Library Screen

## Completed

- Created SDD proposal, spec, design, tasks, and state.
- RED: added LibraryScreen tests for default hidden Missing column and toggle behavior; focused pytest failed on missing `_MISSING_COLUMN` import before production code existed.
- GREEN: added `_MISSING_COLUMN`, `missing_column_button`, session-local visibility state, `_toggle_missing_column()`, accessibility name, tab order, and default hidden column state in `LibraryScreen`.
- REFACTOR/VERIFY: fixed import ordering after Ruff, reran focused and full verification successfully.

## Notes

- Toggle button will live in LibraryScreen top controls.
- Missing column hidden by default.
- No audio files were mutated; no DSP scope added; no MainWindow or other screens changed.

## TDD Cycle Evidence

| Task | RED | GREEN | REFACTOR |
|---|---|---|---|
| LibraryScreen Missing column toggle | `uv run pytest tests/test_library_screen.py -q` failed during collection because `_MISSING_COLUMN` was not implemented. | `uv run pytest tests/test_library_screen.py -q` passed with 3 tests after production code. | Ruff import ordering fixed; ordered verification commands passed. |
