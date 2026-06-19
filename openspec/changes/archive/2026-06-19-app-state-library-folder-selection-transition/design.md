# Design: App State Library Folder Selection Transition

## Approach
Add `apply_library_folder_selected(state, folder)` to `desktop.app_state_transitions`. The helper composes the existing scan-reset policy while preserving the new selected folder.

## Affected Files
- `src/xfinaudio/desktop/app_state_transitions.py`
- `src/xfinaudio/desktop/library_controller.py`
- `tests/test_app_state_transitions.py`
- `openspec/specs/desktop-main-window/spec.md`

## Safety
No audio files are mutated. No DSP scope is added. No Serato DB V2 writes are introduced.
