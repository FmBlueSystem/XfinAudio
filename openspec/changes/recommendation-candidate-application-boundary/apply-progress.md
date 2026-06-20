# Apply Progress

- 2026-06-20: Started boundary slice after archiving strategy catalog boundary.
- 2026-06-20: RED added application candidate-planning tests and desktop import-boundary expectation; focused run failed because `xfinaudio.application.recommendation_candidates` did not exist and `MainWindow` imported recommendation internals directly.
- 2026-06-20: GREEN added `plan_recommendation_candidates()` application boundary and updated `MainWindow._desktop_recommendation_records()` to delegate through it.
