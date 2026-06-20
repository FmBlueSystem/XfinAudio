# Spec: Recommendation shell methods explicit

## Requirement: Recommendation methods are explicit MainWindow methods

Given the desktop shell compatibility map
When the Recommendation slice is applied
Then `recommend_playlist`, `_begin_recommendation_state`, `_end_recommendation_state`, `_start_recommendation_worker`, `_finish_recommendation`, `_fail_recommendation`, `_populate_dj_readiness_table`, and `_on_recommend_requested` are not present in `LEGACY_LAYOUT_METHODS`
And each name is defined directly on `MainWindow`.

## Requirement: Recommendation behavior remains delegated

Given existing recommendation UI actions and worker lifecycle events
When the explicit `MainWindow` methods are called
Then they delegate to the same recommendation service behavior as before.

## Requirement: Bridge and spectral grafts stay stable

Given remaining legacy layout methods outside the Recommendation group
When the Recommendation slice is applied
Then `_on_copilot_variant_applied` and spectral completion grafts remain in `LEGACY_LAYOUT_METHODS` for future slices.
