# Tasks: Playlist Build Log + Genre Cohesion

## Review Workload Forecast
- 400-line budget risk: High (multi-file feature)
- Chained PRs recommended: Yes
- Decision needed before apply: Resolved — user approved full scope; deliver as chained PRs.
- Chain strategy: stacked-to-main, one PR per unit.

## Phase 1 — Unit 1: Genre token fix (scoring) — COMPLETE
- [x] 1.1 RED: test that `_score_tags` returns overlap > 0 for `"House, Disco"` / `"House, Funk"`.
- [x] 1.2 Extract shared `normalize_genre_tokens(genre)` helper; use it in `_normalized_tags`.
- [x] 1.3 De-duplicate `playlist_service._genre_tokens` to reuse the shared helper.
- [x] 1.4 GREEN + run focused scoring tests; harness baseline shows no regression
      (harmonic_journey fill=1.000 collapse=0 validity=0.958).

## Phase 2 — Unit 2: Genre cohesion + slider — CORE COMPLETE
- [x] 2.1 RED: penalty 0 for same genre, > 0 cross genre when cohesion > 0, 0 when cohesion = 0.
- [x] 2.2 Add `genre_cohesion` to `TransitionScoringConfig` + `ScoringSettings` (default 0.0).
- [x] 2.3 Implement `_genre_cohesion_penalty` and apply in `score_transition`.
- [x] 2.5 Add "Genre Cohesion" slider to Build screen + thread through workflow/controller/
      coordinator + persist setting (`ScoringSettings.genre_cohesion`).
- [x] 2.6 GREEN + harness: harmonic_journey cross_genre 0.284 (cohesion 0) → 0.176 (0.5) → 0.169
      (1.0); fill stays ~1.0, validity 0.935→0.915. Added `_cross_genre_fraction` harness metric.

## Phase 3 — Unit 3: Build log — COMPLETE
- [x] 3.1 RED: `recommend_playlist` returns a `PlaylistBuildLog` whose stage drop counts reconcile.
- [x] 3.2 New `recommendation/build_log.py` models (frozen Pydantic) + `build_genre_relations` /
      `count_cross_genre` pure helpers.
- [x] 3.3 Accumulate stages in `recommend_playlist` (`_build_playlist_build_log`); attach log to
      `PlaylistRecommendation.build_log`.
- [x] 3.4 Build log rides on `PlaylistRecommendation`, so it is already available through
      `RecommendationWorkflowResult.recommendation` (no extra workflow field needed).
- [x] 3.5 Embed `build_log` in exported playlist JSON.
- [x] 3.6 Read-only build-log summary on the Review screen via `ReviewViewModel.build_log_summary`
      (reads `state.last_recommendation.build_log`; no separate AppState field required).

## Phase 4 — Verification — COMPLETE
- [x] 4.1 `uv run pytest -q` → 937 passed
- [x] 4.2 `uv run pyright src tests` → 0 errors
- [x] 4.3 `uv run pytest --cov --cov-fail-under=70 -q` → 89.86%
- [x] 4.4 `uv run ruff check .` + `uv run ruff format --check .` → clean
- [x] 4.5 `uv run python scripts/release_gate_check.py --run` → PASS
- [x] 4.6 Harness evidence captured in verify-report.md (cross_genre 0.284→0.176→0.169).

## Deferred follow-ups (out of scope for this change — tracked separately, not blocking)
- Wire the Build-screen "Genre focus" text box into normal `recommend_playlist`. The new Genre
  Cohesion slider already delivers the genre-mixing reduction; the text-box wiring is a small,
  independent follow-up and is intentionally NOT part of this change's acceptance criteria.
