# Apply Progress: Hidden Bug Hardening

Status: implementation complete; verified; ready to archive.

## Completed

- Recommendation BPM validation now runs after sequencing and validates final order.
- UI filtering/folder changes clear stale selections and constraints.
- `show_tracks` updates app state before rendering.
- Genre display loads preserve `genre_decision`.
- Enrichment service skips disabled providers.
- Settings dialog preserves non-UI genre settings.
- Runtime providers do not cache transient failures.
- Desktop scan workflow receives an enrichment service factory using current settings.

## Focused Verification

- `uv run pytest tests/genre/test_enrichment_service.py tests/genre/test_settings_extension.py tests/genre/test_lastfm_provider.py tests/genre/test_spotify_provider.py tests/genre/test_deezer_provider.py tests/test_track_repository.py tests/test_library_view_model.py tests/test_settings_dialog.py tests/test_main_window.py tests/test_playlist_service.py tests/test_playlist_workflow.py -q` -> 230 passed.

## Full Verification

- `uv run pytest -q` -> 1074 passed, 2 warnings.
- `uv run pyright src tests` -> 0 errors, 0 warnings.
- `uv run pytest --cov --cov-fail-under=70 -q` -> 89.60% coverage, gate passed.
- `uv run ruff check .` -> all checks passed.
- `uv run ruff format --check .` -> 232 files already formatted.
- `uv run python scripts/release_gate_check.py --run` -> PASS.
