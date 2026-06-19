# Apply Progress: AppState Prep Copilot variant transition boundary

## Completed

- RED: Added focused test for immutable Prep Copilot variant application and observed failure because the helper did not exist.
- GREEN: Added `PrepCopilotVariantApplication` and `apply_prep_copilot_variant()` to `app_state_transitions.py`.
- REFACTOR: Updated `PrepCopilotController.apply_selected_variant()` to delegate AppState update policy to the helper and replace AppState through the existing host boundary when available.

## Evidence

- Initial focused test failed on missing helper.
- Focused Prep Copilot regressions passed after routing replacement through `_replace_app_state()`.
- `uv run pyright src tests` passed.
