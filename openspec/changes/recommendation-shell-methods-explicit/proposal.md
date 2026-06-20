# Proposal: Recommendation shell methods explicit

## Intent

Remove the Recommendation group from dynamic `shell_layout_compat.LEGACY_LAYOUT_METHODS` grafting by defining explicit `MainWindow` methods that delegate to existing recommendation service behavior.

## Scope

In scope:
- `recommend_playlist`
- `_begin_recommendation_state`
- `_end_recommendation_state`
- `_start_recommendation_worker`
- `_finish_recommendation`
- `_fail_recommendation`
- `_populate_dj_readiness_table`
- `_on_recommend_requested`
- Regression coverage proving those methods are explicit `MainWindow` methods and absent from the graft map.
- Architecture and elimination-plan documentation updates.

Out of scope:
- `_on_copilot_variant_applied` bridge method, which remains for a later slice.
- Changing recommendation algorithms or scoring behavior.
- Changing export behavior.
- Mutating audio files.
- Adding DSP or live Serato DB V2 writes.

## Risk and rollback

Risk is limited to method wiring. Roll back by restoring the graft-map entries and removing the explicit delegators.

## Success criteria

- The eight Recommendation names are absent from `LEGACY_LAYOUT_METHODS`.
- `MainWindow` exposes explicit callable methods for all eight names.
- `_on_copilot_variant_applied` remains in the graft map for its dedicated bridge slice.
- Existing focused and full verification gates pass.
- The legacy layout graft map count drops from 14 to 6.
