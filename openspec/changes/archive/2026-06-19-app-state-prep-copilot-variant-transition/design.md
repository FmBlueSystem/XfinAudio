# Design: AppState Prep Copilot variant transition boundary

## Approach
Add a pure helper to `src/xfinaudio/desktop/app_state_transitions.py` that accepts the selected variant's computed application payload and returns a new AppState.

## Candidate API
`apply_prep_copilot_variant(state, payload) -> AppState`

The payload should expose:
- `recommendation`
- `explanation`
- `quality_report`
- `readiness_report`
- `variant_name`

The helper must use `state.model_copy(update=...)`, clear `playlist_removed_paths`, and avoid PySide6 dependencies.

## Affected files
- `src/xfinaudio/desktop/app_state_transitions.py`
- `src/xfinaudio/desktop/prep_copilot.py`
- `tests/test_app_state_transitions.py`
- `openspec/specs/desktop-main-window/spec.md`

## Safety
No audio files are modified. No DSP is added. No Serato DB V2 writes are introduced.
