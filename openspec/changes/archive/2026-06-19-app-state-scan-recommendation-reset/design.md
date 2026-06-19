# Design: AppState scan recommendation reset boundary

## Approach
Add a pure helper to `src/xfinaudio/desktop/app_state_transitions.py` that owns the AppState reset policy for scan-dependent recommendation context. Desktop code should call the helper rather than manually clearing recommendation fields.

## API
`apply_scan_context_reset(state: AppState) -> AppState`

The helper must:
- use `state.model_copy(update=...)`;
- not mutate the input state;
- clear scan records and records-by-path;
- clear stale recommendation result fields;
- clear removed playlist paths and applied Prep Copilot variant;
- preserve unrelated track constraints;
- avoid PySide6 dependencies.

## Affected files
- `src/xfinaudio/desktop/app_state_transitions.py`
- `src/xfinaudio/desktop/library_controller.py`
- `tests/test_app_state_transitions.py`
- `openspec/specs/desktop-main-window/spec.md`

## Safety
No audio files are modified. No DSP is added. No Serato DB V2 writes are introduced.
