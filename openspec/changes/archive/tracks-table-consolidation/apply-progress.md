# Apply Progress: Consolidate Tracks Table Ownership

## Completed

- Removed the dead `MainWindow.tracks_table` construction and migrated MainWindow table operations to `LibraryScreen.tracks_table`.
- Updated library-table column constants for the 12-column LibraryScreen layout.
- Updated `populate_library_table` to populate Duration and Preview columns and keep Path at column 11.
- Updated tests and integration smoke references from `window.tracks_table` to `window._library_screen.tracks_table`.

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 4. MainWindow has no tracks_table | `tests/test_main_window.py` | Integration/UI | ✅ 95/95 focused tests passed before edits | ✅ `test_main_window_does_not_create_dead_tracks_table` failed against existing code | ✅ Focused suite passed after implementation | ✅ Existing constructor/table contract tests assert LibraryScreen column layout | ✅ Removed dead table setup and routed callers to LibraryScreen |
| 5. All writes go to LibraryScreen.tracks_table | `tests/test_main_window.py`, `tests/test_table_populators.py`, `tests/integration_flow.py` | Integration/UI + unit | ✅ Same focused baseline | ✅ Existing tests were updated to visible LibraryScreen table and failed until production migration | ✅ Focused suite and table populator suite passed | ✅ Sort, filter, selection, spectral update, and population paths covered | ✅ Consolidated table column constants and compact width mapping |
| 6. Verify | Verification commands | Release gate | ✅ Focused tests green before full gate | N/A | ✅ All required commands passed | N/A | ✅ Ruff format/check passed |

## Verification

- `uv run pytest tests/test_main_window.py tests/test_library_screen.py -q` — PASS, 96 passed.
- `uv run pytest -q` — PASS, 811 passed, 2 warnings.
- `uv run pyright src tests` — PASS, 0 errors.
- `uv run pytest --cov --cov-fail-under=70 -q` — PASS, 88.52% coverage.
- `uv run ruff check .` — PASS.
- `uv run ruff format --check .` — PASS.
- `uv run python scripts/release_gate_check.py --run` — PASS.

## Notes

- No audio files were mutated.
- No DSP scope was added.
- `openspec/changes/playlist-export-hardening` was not touched.
