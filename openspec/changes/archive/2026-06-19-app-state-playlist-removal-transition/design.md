# Design: AppState playlist removal transition boundary

## Approach
Add pure helpers to `src/xfinaudio/desktop/app_state_transitions.py`:

- `apply_playlist_track_removed(state: AppState, path: str) -> AppState`
- `apply_playlist_track_restored(state: AppState, path: str) -> AppState`

Both helpers use `state.model_copy(update=...)`, update only `playlist_removed_paths`, and avoid PySide6 dependencies.

## Affected files
- `src/xfinaudio/desktop/app_state_transitions.py`
- `src/xfinaudio/desktop/library_controller.py`
- `tests/test_app_state_transitions.py`
- `openspec/specs/desktop-main-window/spec.md`

## Safety
No audio files are modified. No DSP is added. No Serato DB V2 writes are introduced.
