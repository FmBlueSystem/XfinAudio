# Apply Progress: AppState playlist removal transition boundary

## Completed

- RED: Added focused tests for immutable playlist remove/restore transitions and observed failures because the helpers did not exist.
- GREEN: Added `apply_playlist_track_removed()` and `apply_playlist_track_restored()` to `app_state_transitions.py`.
- REFACTOR: Updated `LibraryController.apply_track_removed()` and `LibraryController.apply_track_restored()` to delegate state policy to the helpers.

## Evidence

- Initial focused tests failed on missing helpers.
- `uv run pytest tests/test_app_state_transitions.py tests/test_main_window.py::test_track_removal_is_undoable_and_redoable -q` passed.
- `uv run pyright src tests` passed.
