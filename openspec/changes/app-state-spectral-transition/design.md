# AppState Spectral Transition Design

## Architecture
Add `xfinaudio.desktop.app_state_transitions` as a pure desktop-state transition module. It depends on `AppState`, `TrackRecord`, and `SpectralProfile`, but not on PySide6 widgets or controller state.

`LibraryController.on_spectral_profile_ready` will:
1. replace direct list/dict mutation with `apply_spectral_profile()`;
2. push the returned state through `state_setter` so other desktop components see the same state instance;
3. keep table-cell rendering in the controller.

## Safety
- Use `state.model_copy(update=...)` with copied collections.
- Do not mutate `scanned_records` or `records_by_path` in place.
- Do not change worker behavior or repository writes.
- No audio mutation, no DSP expansion, no Serato DB writes.

## Testing
Add `tests/test_app_state_transitions.py` with RED-first tests for immutability, synchronized updates, and unknown-path behavior.
