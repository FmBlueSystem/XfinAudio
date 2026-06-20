# Remove Recommendation Presenter Wrapper Specification

## Requirement: Desktop does not re-export recommendation policy
- GIVEN source code imports WHEN recommendation candidate policy is needed THEN callers use recommendation/application modules directly, not `xfinaudio.desktop.recommendation_presenter`.

## Requirement: Existing recommendation behavior remains unchanged
- GIVEN existing candidate-pool tests WHEN the wrapper is removed THEN behavior tests continue to pass unchanged.
