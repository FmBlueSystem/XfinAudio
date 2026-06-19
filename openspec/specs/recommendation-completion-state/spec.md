# Spec: Recommendation Completion State Transition

## Requirement: Completed recommendation state is applied immutably

### Scenario: Recommendation completes
GIVEN an existing `AppState` with prior recommendation state, removed playlist paths, and an applied variant
WHEN a completed recommendation result is applied
THEN a new `AppState` is returned
AND `last_recommendation`, `last_playlist_explanation`, and `last_quality_report` come from the result
AND `playlist_removed_paths` is reset to an empty `frozenset`
AND `applied_variant_name` is cleared
AND the original `AppState` remains unchanged.

## Requirement: RecommendationService applies completion to the current state

### Scenario: State changed before worker completion
GIVEN the desktop state can be replaced while a recommendation worker is running
WHEN `RecommendationService.on_completed()` handles the worker result
THEN it reads the current `AppState` through its state accessor
AND it passes a new completed-recommendation state to the state setter
AND it does not depend on a stale captured `AppState` instance.

## Requirement: Desktop controllers stay synchronized after state replacement

### Scenario: AppState is replaced by a pure transition
GIVEN `replace_app_state()` publishes a new `AppState`
WHEN later desktop controllers clear scan-dependent state or render Prep Copilot status
THEN `LibraryController` uses the replacement state
AND `RecommendationService` remains compatible with future `replace_app_state()` calls
AND the applied Prep Copilot variant badge is cleared for a normal recommendation.

## Requirement: RecommendationService keeps UI responsibility

### Scenario: Service handles completion
GIVEN a completed background recommendation result
WHEN `RecommendationService.on_completed()` runs
THEN it delegates only the AppState transition to the pure helper
AND it continues to render recommendation UI, review summary, readiness, transition review, status, export guidance, and Prep Copilot badge state itself.
