# Design: AppState saved playlist export transition boundary

## Approach
Add `apply_saved_playlist_export_recommendation(state: AppState, recommendation: PlaylistRecommendation) -> AppState` to `app_state_transitions.py`.

`PlaylistCoordinator.export_playlist()` will continue constructing the recommendation from saved playlist tracks, but will delegate AppState replacement to the helper and use `_replace_app_state` when the host provides it.

## Affected files
- `src/xfinaudio/desktop/app_state_transitions.py`
- `src/xfinaudio/desktop/playlist_coordinator.py`
- `tests/test_app_state_transitions.py`
- `tests/test_playlist_coordinator.py`
- `openspec/specs/desktop-main-window/spec.md`

## Safety
No audio files are modified. No DSP is added. No Serato DB V2 writes are introduced.
