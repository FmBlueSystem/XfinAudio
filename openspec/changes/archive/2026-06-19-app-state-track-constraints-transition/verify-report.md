# Verify Report: AppState track constraints transition boundary

## Result

PASS.

## Requirement evidence

### Immutable track constraint transitions

- `apply_tracks_excluded()` returns a new AppState and preserves existing excluded paths.
- `apply_tracks_locked()` returns a new AppState and preserves existing locked paths.
- `apply_track_constraints_cleared()` returns a new AppState with excluded and locked paths cleared.
- `LibraryController` delegates constraint mutation policy to pure helpers while keeping selection reading and UI sync in desktop.

## Commands

- `uv run pytest tests/test_app_state_transitions.py tests/test_main_window.py -q` — PASS, 122 tests.
- `uv run pyright src tests` — PASS, 0 errors.
- `uv run python scripts/release_gate_check.py --run` — PASS, 892 tests, coverage 90.16%, ruff, format, release smoke, docs, artifact hygiene, source package hygiene, PyInstaller check-only, root artifact hygiene.

## Safety

- No audio files mutated.
- No DSP scope added.
- No Serato DB V2 writes added.
