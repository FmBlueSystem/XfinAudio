# Tasks: Spectral Cohesion Control

1. [x] **Proposal** — document intent, scope, risks, and success criteria.
2. [x] **Specification** — write GIVEN/WHEN/THEN scenarios for scoring, UI, and wiring.
3. [x] **Design** — choose slider + strategy route using Arbor-style comparison; define scoring formula.
4. [x] **TDD: scoring cohesion** — RED/GREEN/REFACTOR
   - [x] RED: add tests proving high cohesion penalizes different colors and boosts same-color weight.
   - [x] GREEN: implement `spectral_cohesion` in `TransitionScoringConfig`, `_effective_weights`, `_spectral_color_penalty`.
   - [x] REFACTOR: keep `score_transition` readable; clamp total score to `[0, 1]`.
5. [x] **TDD: optimizer wiring** — pass `TransitionScoringConfig` through `recommend_sequence` and `_score_matrix`.
6. [x] **TDD: playlist service** — accept `spectral_cohesion` in `recommend_playlist` and use it for final scoring.
7. [x] **Add Same Color strategy** — register in `StrategyName` and `_STRATEGIES`.
8. [x] **Application wiring** — forward `spectral_cohesion` through `PlaylistWorkflowService`, `RecommendationController`, `RecommendationCoordinator`.
9. [x] **UI control** — add slider to `BuildScreen`, emit `spectral_cohesion_changed`, expose accessor.
10. [x] **Persistence** — add `spectral_cohesion` to `ScoringSettings`; initialize and persist slider value in `MainWindow`.
11. [x] **Update existing tests** — strategy count, main window strategy combo count.
12. [x] **Verify** — run all verification commands and produce `verify-report.md`.
