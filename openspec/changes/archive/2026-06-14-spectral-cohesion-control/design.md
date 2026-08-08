# Design: Spectral Cohesion Control

## Decision question

How should the DJ control the influence of spectral color on playlist cohesion without locking them into a single strategy?

## Alternatives considered (Arbor-style)

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| **A. Fixed high spectral weight in all strategies** | Simple; same color always preferred. | No way to opt out; contradicts user's need for variety. | Rejected. |
| **B. Only a "Same Color" strategy** | Clear product intent; no new UI widgets. | Coarse control; DJ must switch strategies to change cohesion. | Partial: keep as shortcut, but not the only control. |
| **C. Per-strategy spectral weight overrides** | Strategies fully define behavior. | Hidden from user; requires editing strategy code to tune. | Rejected. |
| **D. Continuous cohesion slider + Same Color strategy** | Fine-grained control; visible and persisted; power users can use the strategy shortcut. | One extra UI element. | **Selected.** |

## Architecture impact

```text
BuildScreen (slider)
    │ spectral_cohesion_changed(int 0-100)
    ▼
MainWindow._on_spectral_cohesion_changed
    │ persists to AppSettings.scoring.spectral_cohesion
    ▼
RecommendationCoordinator.recommend
    │ reads slider, converts to float
    ▼
RecommendationController.start_recommendation(spectral_cohesion)
    ▼
PlaylistWorkflowService.recommend(spectral_cohesion)
    ▼
recommend_playlist(spectral_cohesion)
    │ builds TransitionScoringConfig(weights=..., spectral_cohesion=...)
    ▼
recommend_sequence(config=scoring_config) → score_transition(config=scoring_config)
```

## Scoring formula

```python
# Effective spectral weight increases with cohesion
effective_spectral_weight = weights.spectral * (1.0 + spectral_cohesion)

# Dominant-color penalty only when colors differ
color_penalty = 0.0
if both_profiles_present and left.dominant_color != right.dominant_color:
    color_penalty = spectral_cohesion * 0.25

total_score = clamp(weighted_component_score - color_penalty, 0.0, 1.0)
```

With `cohesion=0.0` the formula reduces to the pre-existing behavior. With `cohesion=1.0`, spectral weight doubles and a different dominant color costs up to 0.25 points.

## Affected files

- `src/xfinaudio/config/settings.py` — `ScoringSettings.spectral_cohesion`.
- `src/xfinaudio/recommendation/scoring.py` — `TransitionScoringConfig`, effective weights, color penalty.
- `src/xfinaudio/recommendation/optimizer.py` — thread `TransitionScoringConfig` through `recommend_sequence` and `_score_matrix`.
- `src/xfinaudio/recommendation/playlist_service.py` — accept `spectral_cohesion`, build config, use it for final scoring.
- `src/xfinaudio/recommendation/strategies.py` — `same_color` strategy.
- `src/xfinaudio/application/playlist_workflow.py` — forward `spectral_cohesion` to `recommend_playlist`.
- `src/xfinaudio/desktop/recommendation_controller.py` — accept and forward `spectral_cohesion`.
- `src/xfinaudio/desktop/recommendation_coordinator.py` — read slider value and pass it.
- `src/xfinaudio/desktop/screens/build_screen.py` — slider, label, signal, accessor.
- `src/xfinaudio/desktop/main_window.py` — initialize slider from settings, persist on change.

## Safety

- No audio mutation.
- No DSP scope expansion; reuse existing read-only spectral profiles.
- Missing profiles degrade gracefully (no penalty, no weight).
- Backward-compatible default in scoring config (`spectral_cohesion=0.0`).
