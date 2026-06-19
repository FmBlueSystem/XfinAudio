# Apply Progress: AppState saved playlist export transition boundary

## Completed

- RED: Added focused test for immutable saved-playlist export recommendation replacement and observed failure because the helper did not exist.
- GREEN: Added `apply_saved_playlist_export_recommendation()` to `app_state_transitions.py`.
- REFACTOR: Updated `PlaylistCoordinator.export_playlist()` to delegate AppState recommendation replacement to the helper and use host AppState replacement when available.

## Evidence

- Initial focused test failed on missing helper.
- `uv run pytest tests/test_app_state_transitions.py::test_apply_saved_playlist_export_recommendation_returns_new_state_without_mutating_original tests/test_playlist_coordinator.py -q` passed.
- `uv run pyright src tests` passed.
