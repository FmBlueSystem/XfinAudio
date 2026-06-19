# Proposal: Recommendation Completion State Transition

## Intent
Extract the AppState update performed after a recommendation completes into a pure transition helper.

## Scope
- Add tests for the completed recommendation AppState transition.
- Add a pure helper in `src/xfinaudio/desktop/app_state_transitions.py`.
- Update `RecommendationService.on_completed()` to use the helper while keeping UI rendering in the service.

## Out of Scope
- Recommendation algorithm changes.
- Export behavior changes.
- UI redesign or label changes.
- Audio mutation, DSP, or Serato DB V2 writes.

## Risks
- Accidentally preserving stale playlist removal or prep-copilot variant state.
- Accidentally moving UI rendering concerns into state transition code.

## Success Criteria
- The helper returns a new `AppState` and leaves the original unchanged.
- Completion fields are stored, playlist removals are reset, and applied variant is cleared.
- Focused transition tests pass and static type checking is attempted.
