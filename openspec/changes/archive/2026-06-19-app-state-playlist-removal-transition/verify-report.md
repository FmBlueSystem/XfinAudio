# Verify Report: AppState playlist removal transition boundary

## Result

PASS.

## Requirement evidence

### Immutable playlist removal transitions

- `apply_playlist_track_removed()` returns a new AppState and preserves existing removed paths.
- `apply_playlist_track_restored()` returns a new AppState and preserves unrelated removed paths.
- `LibraryController` delegates remove/restore state policy to the pure helpers while keeping undo and synchronization orchestration in desktop.

## Commands

- `uv run pytest tests/test_app_state_transitions.py tests/test_main_window.py -q` — PASS, 118 tests.
- `uv run pyright src tests` — PASS, 0 errors.
- `uv run python scripts/release_gate_check.py --run` — PASS, 888 tests, coverage 90.17%, ruff, format, release smoke, docs, artifact hygiene, source package hygiene, PyInstaller check-only, root artifact hygiene.

## Safety

- No audio files mutated.
- No DSP scope added.
- No Serato DB V2 writes added.
