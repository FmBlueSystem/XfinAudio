# Design: AppState Prep Copilot plan transition boundary

## Approach
Add pure helpers to `src/xfinaudio/desktop/app_state_transitions.py`:

- `apply_prep_copilot_plan_generated(state: AppState, plan: PrepCopilotPlan) -> AppState`
- `apply_prep_copilot_plan_cleared(state: AppState) -> AppState`

`PrepCopilotController.generate()` will call the helpers and replace host AppState through `_replace_app_state` when available.

## Affected files
- `src/xfinaudio/desktop/app_state_transitions.py`
- `src/xfinaudio/desktop/prep_copilot.py`
- `tests/test_app_state_transitions.py`
- `openspec/specs/desktop-main-window/spec.md`

## Safety
No audio files are modified. No DSP is added. No Serato DB V2 writes are introduced.
