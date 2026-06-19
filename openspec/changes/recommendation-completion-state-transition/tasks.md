# Recommendation Completion State Transition Tasks

- [x] 1. RED: Add a focused failing test for completed recommendation AppState transition.
- [x] 2. GREEN: Implement `apply_recommendation_completion()` with immutable `AppState.model_copy(update=...)`.
- [x] 3. RED: Add a focused failing test that `RecommendationService` applies completion to the current state accessor.
- [x] 4. GREEN: Update `RecommendationService.on_completed()` to use the helper with the current state accessor.
- [x] 5. RED: Add regression tests for `replace_app_state()` compatibility, LibraryController state refresh, and Prep Copilot badge clearing.
- [x] 6. GREEN: Keep controller state references synchronized and keep UI badge clearing in the desktop service.
- [x] 7. VERIFY: Run focused transition/service tests, Pyright, focused Ruff checks, and diff hygiene.
- [x] 8. VERIFY: Run full XfinAudio gates before PR.
