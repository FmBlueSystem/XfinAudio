# Proposal: Spectral Cohesion Control

## Intent

Give the DJ a variable knob that controls how much spectral color (RED/GREEN/BLUE/MIXED) influences playlist recommendations. Same color should sound similar and be preferred when cohesion is high, but the DJ must be able to disable or weaken that constraint when variety is desired.

## Scope

### In scope

- Add a runtime `spectral_cohesion` parameter to transition scoring (0.0 = neutral, 1.0 = strong cohesion).
- Scale the spectral component weight by `(1 + cohesion)`.
- Apply a small penalty when adjacent tracks have different dominant colors, proportional to cohesion.
- Add a "Same Color" playlist strategy that maximizes spectral cohesion by default.
- Add a UI slider in Build Playlist (0%–100%) backed by persisted `AppSettings`.
- Thread the value from the UI through `MainWindow`, `RecommendationCoordinator`, `RecommendationController`, `PlaylistWorkflowService`, and `recommend_playlist`.

### Out of scope

- Changing the spectral analyzer or color definitions.
- Filtering tracks by color.
- Real-time analysis during playback.
- Audio mutation or DSP expansion.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Existing scoring behavior changes unexpectedly | Default `spectral_cohesion=0.0` in scoring config preserves existing behavior; app default is 0.5 via settings only for new UI interactions. |
| Missing spectral profiles reduce cohesion effect | Penalty and weight scaling only apply when both tracks have profiles; missing profiles degrade gracefully. |
| UI slider adds clutter | Kept compact, placed under strategy explanation, with a clear percentage label. |

## Success criteria

1. Slider value persists across app restarts.
2. High cohesion lowers the score of RED→GREEN transitions relative to low cohesion.
3. Same-color transitions are not penalized at any cohesion level.
4. "Same Color" strategy appears in the strategy combo and uses high spectral weight.
5. All verification commands pass.

## Rollback plan

- Revert `ScoringSettings.spectral_cohesion` default to `0.0` and remove UI slider; scoring logic remains backward-compatible because `spectral_cohesion=0.0` disables the new effects.

## Review budget

Estimated changed lines for this slice: ~200 production + ~80 test lines, within the 400-line budget.
