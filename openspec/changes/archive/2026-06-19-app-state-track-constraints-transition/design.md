# Design: AppState track constraints transition boundary

## Approach
Add pure helpers to `src/xfinaudio/desktop/app_state_transitions.py`:

- `apply_tracks_excluded(state: AppState, paths: Iterable[str]) -> AppState`
- `apply_tracks_locked(state: AppState, paths: Iterable[str]) -> AppState`
- `apply_track_constraints_cleared(state: AppState) -> AppState`

Helpers must use `state.model_copy(update=...)` and avoid PySide6 dependencies.

## Affected files
- `src/xfinaudio/desktop/app_state_transitions.py`
- `src/xfinaudio/desktop/library_controller.py`
- `tests/test_app_state_transitions.py`
- `openspec/specs/desktop-main-window/spec.md`

## Safety
No audio files are modified. No DSP is added. No Serato DB V2 writes are introduced.
