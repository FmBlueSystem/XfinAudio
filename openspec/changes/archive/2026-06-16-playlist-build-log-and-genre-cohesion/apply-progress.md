# Apply Progress: Playlist Build Log + Genre Cohesion

Mode: Strict TDD. Chained PRs (stacked-to-main), one per unit.

## TDD Cycle Evidence

| Task | RED | GREEN | REFACTOR |
|------|-----|-------|----------|
| 1.1 comma-split genre overlap | `test_score_transition_splits_comma_separated_genres_for_overlap` failed (0.0 vs 1/3) | passes after `normalize_genre_tokens` | extracted shared helper |
| 1.2 shared helper | — | `_normalized_tags` uses `normalize_genre_tokens` | — |
| 1.3 de-dup | — | `playlist_service._genre_tokens` delegates to helper | removed duplicate split logic |

## Unit 1 — COMPLETE
Files changed:
- `src/xfinaudio/recommendation/scoring.py` — new `normalize_genre_tokens()`, `_normalized_tags` comma-splits genre.
- `src/xfinaudio/recommendation/playlist_service.py` — `_genre_tokens` delegates to shared helper.
- `tests/test_transition_scoring.py` — 2 new tests (same-family overlap > 0; unrelated = 0).

Evidence: focused suites green (test_transition_scoring, test_playlist_service, test_recommendation_eval = 69 passed). Harness: harmonic_journey fill=1.000 collapse=0 validity=0.958 (no regression).

## Unit 2 — CORE COMPLETE (genre cohesion + slider)

| Task | RED | GREEN | REFACTOR |
|------|-----|-------|----------|
| 2.1 genre penalty | `test_genre_cohesion_penalizes_cross_genre_transition` failed (0.9==0.9) | passes after `_genre_cohesion_penalty` | — |
| 2.5 slider | `test_genre_cohesion_slider_emits_and_reports_value` failed (no attr) | passes after slider + signal | mirrored spectral exactly |

Files changed:
- `recommendation/scoring.py` — `genre_cohesion` config field + `_genre_cohesion_penalty`, applied in `score_transition`.
- `recommendation/playlist_service.py` — `recommend_playlist(genre_cohesion=...)` threads into scoring config.
- `recommendation/evaluation.py` + `scripts/eval_recommendation.py` — `_cross_genre_fraction` metric, `--genre-cohesion` CLI.
- `application/playlist_workflow.py`, `desktop/recommendation_controller.py`, `desktop/recommendation_coordinator.py` — threaded `genre_cohesion`.
- `desktop/screens/build_screen.py` — Genre Cohesion slider + signal + value method.
- `desktop/main_window.py` — init slider from settings, connect, persist `_on_genre_cohesion_changed`.
- `config/settings.py` — `ScoringSettings.genre_cohesion` (default 0.0).
- `desktop/theme.py` — readiness semaphore pill colors (also from the Review-screen polish).
- Tests: test_transition_scoring, test_recommendation_eval, test_build_screen.

Evidence: full suite 929 passed, pyright 0 errors, ruff clean, coverage 89.76%, release gate PASS.
Harness: cross_genre 0.284 → 0.176 (cohesion 0.5) → 0.169 (1.0).

Deferred (small follow-up): 2.4 wire the "Genre focus" text box into normal recommend.

## Unit 3 — COMPLETE (build log)

| Task | RED | GREEN | REFACTOR |
|------|-----|-------|----------|
| 3.1 build log attached | `test_recommend_playlist_attaches_build_log...` failed (no attr) | passes after `build_log` field + `_build_playlist_build_log` | — |
| 3.2 models | `test_build_log.py` import error | passes after `build_log.py` | pure helpers extracted |
| 3.5 JSON embed | `test_export_playlist_json...` build_log assert failed | passes after exporter embed | — |
| 3.6 UI summary | `TestBuildLogSummary` failed (no method) | passes after `build_log_summary` | — |

Files changed:
- NEW `recommendation/build_log.py` — `BuildStage`, `TransitionGenreRelation`, `PlaylistBuildLog`, `build_genre_relations`, `count_cross_genre`.
- `recommendation/playlist_service.py` — `PlaylistRecommendation.build_log` field + `_build_playlist_build_log` assembles stage funnel + genre relations.
- `exporting/playlist_exporters.py` — `build_log` embedded in playlist JSON.
- `desktop/review_view_model.py` — `build_log_summary(state)`.
- `desktop/screens/review_screen.py` — read-only `build_log_label` rendered from the VM.
- Tests: test_build_log (new), test_playlist_service, test_playlist_exporters, test_review_view_model.

Evidence: full suite 937 passed, pyright 0 errors, ruff + format clean, coverage 89.86%, release gate PASS.

## ALL THREE UNITS COMPLETE — ready for verify/archive.
