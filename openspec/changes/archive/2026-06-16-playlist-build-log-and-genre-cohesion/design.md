# Design: Playlist Build Log + Genre Cohesion

## Architecture boundaries
All work stays in pure functions over `TrackRecord` in `src/xfinaudio/recommendation/` plus the
desktop view/render layer. No audio I/O, no DSP, no Serato writes.

## Unit 1 — Genre token fix (scoring)
**File**: `recommendation/scoring.py`
- `_normalized_tags(track)` currently appends `track.genre` whole. Change to split the genre on
  commas into normalized tokens (reuse the same logic as `playlist_service._genre_tokens`).
- Extract a shared helper `normalize_genre_tokens(genre: str | None) -> set[str]` so scoring and
  `playlist_service` share one definition (kill the duplication).
- No weight change here — purely makes the existing 0.05 tag weight actually fire for same-family
  multi-genre tracks.

**Test (RED first)**: `_score_tags` of two tracks `"House, Disco"` / `"House, Funk"` returns
overlap > 0 (currently 0).

## Unit 2 — Genre cohesion + Genre focus wiring
**Files**: `recommendation/scoring.py`, `recommendation/playlist_service.py`,
`config/settings.py`, desktop build screen/view-model/main_window.

- Add `genre_cohesion: float` (0..1, default 0.0) to `TransitionScoringConfig` /`ScoringSettings`,
  mirroring the existing `spectral_cohesion` pattern (`scoring.py:302-318`).
- Add `_genre_cohesion_penalty(left, right, cohesion)` mirroring `_spectral_color_penalty`:
  0 when genre tokens intersect, `cohesion * k` when they fully mismatch (both have genre).
  Applied as a subtractive penalty on the transition total, same mechanism as spectral.
- Wire the existing Build-screen "Genre focus" value into normal `recommend_playlist`: when set,
  bias the candidate pool toward matching genre tokens (token intersection, casefold) — reuse the
  `same_genre` soft-sort path in `pool.py`, never a hard drop unless explicitly the `same_genre`
  strategy. Default empty = current behavior.
- A new Build-screen slider "Genre Cohesion" (0..100%) mirrors the Spectral Cohesion slider.

**Tests (RED first)**:
- Penalty is 0 for same-genre, positive for cross-genre when cohesion > 0, 0 when cohesion = 0.
- Harness metric: cross-genre transition ratio decreases as cohesion rises (deterministic seed).

## Unit 3 — Build log
**Files**: new `recommendation/build_log.py`, `recommendation/playlist_service.py`,
`application/playlist_workflow.py`, `exporting/playlist_exporters.py`, desktop review/export.

- New frozen Pydantic models:
  - `BuildStage(name, input_count, output_count, dropped, reason)`
  - `TransitionGenreRelation(order, from_track, to_track, relation)` where relation ∈
    {`same`, `overlap`, `cross`}.
  - `PlaylistBuildLog(strategy, optimizer, pool_size, stages, genre_relations, cross_genre_count,
    final_track_count, warnings)`.
- `recommend_playlist` accumulates stages as it already computes drop counts; assemble the log at
  the end and attach it as a new optional field on `PlaylistRecommendation` (frozen `model_copy`).
- Surface via `PlaylistWorkflowService.recommend` into `RecommendationWorkflowResult`.
- Persist: embed `build_log` in the playlist JSON next to the existing `explanation` block.
- UI: a read-only collapsible "Build Log" panel on the Review screen (or Export) listing stages +
  cross-genre count. No new heavy table; reuse a compact text/list rendering.

## AppState immutability
All new state added via `model_copy(update=...)`; build log stored as `last_build_log` mirroring
`last_playlist_explanation` (`app_state.py:32`).

## Risk / measurement
The eval harness (`scripts/eval_recommendation.py` / `recommendation/evaluation.py`) is the
objective gate: report cross-genre ratio, fill rate, hard-rule validity, energy monotonicity
before/after for Units 1 and 2 on the real 10,607-track library with a fixed seed.
