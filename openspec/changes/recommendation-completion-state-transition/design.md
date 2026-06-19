# Design: Recommendation Completion State Transition

## Approach
Add `apply_recommendation_completion(state, result)` to `desktop.app_state_transitions`.

The helper treats `result` as a result-like object with:
- `recommendation`
- `explanation`
- `quality_report`

It returns `state.model_copy(update={...})` and does not mutate the input state.

`RecommendationService` receives a current-state accessor and a state setter. On completion it reads the current state, applies the pure transition, then publishes the replacement state through the setter. It keeps UI-specific work, including clearing the visible Prep Copilot applied-variant badge.

`replace_app_state()` keeps controllers synchronized with the replacement state, including `LibraryController`, so later UI actions do not mutate stale state.

## Affected Files
- `tests/test_app_state_transitions.py` — RED/GREEN coverage for the pure transition.
- `tests/test_recommendation_service_state.py` — RED/GREEN coverage for current-state access, `replace_app_state()` compatibility, Prep Copilot badge clearing, and LibraryController state refresh.
- `src/xfinaudio/desktop/app_state_transitions.py` — new helper and export.
- `src/xfinaudio/desktop/recommendation_service.py` — call the helper from `on_completed()` and keep UI badge clearing in the service.
- `src/xfinaudio/desktop/layout.py` — wire the current state accessor and state setter.
- `src/xfinaudio/desktop/window_factory.py` — keep `LibraryController` synchronized after state replacement.

## Safety
No audio files are mutated. No DSP, export, Serato DB V2, or recommendation algorithm behavior changes are introduced.
