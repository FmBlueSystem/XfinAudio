# Design: Recommendation Quality Harness and Pool-Collapse Fix

## Architecture impact

Additive measurement layer plus a localized fix. No change to the public recommendation API,
the data model, or the desktop UI.

### Pre-existing constraint discovered during apply

`xfinaudio.quality` has a latent circular import: importing the `quality` package before
`xfinaudio.recommendation` fails (`quality.__init__` → `dj_readiness` → … →
`recommendation.prep_copilot` → `quality.dj_readiness` partially initialized). It only works today
because the app imports `recommendation` first. Therefore the harness must NOT live under
`quality/`. Additionally, `build_recommendation_pool` currently lives in
`desktop/recommendation_presenter.py`, whose package `__init__` imports `MainWindow` (Qt) — a
read-only metrics harness must not import the UI framework.

### Refactor (structural, no behavior change)

Move `build_recommendation_pool` and its pure helpers to `src/xfinaudio/recommendation/pool.py`
(its real domain). `desktop/recommendation_presenter.py` re-exports it for backward compatibility,
so existing importers (`main_window.py`, `test_recommendation_presenter.py`) keep working
unchanged. Existing presenter tests are the safety net for this move.

### New module

`src/xfinaudio/recommendation/evaluation.py` — pure, importable, testable evaluation logic
(placed in the recommendation domain to avoid the quality-package import cycle and Qt):

- `EvalConfig` (frozen pydantic): `seed: int`, `sample_size: int`, `requested_size: int`,
  `candidate_limit: int`, `strategies: tuple[str, ...]`.
- `StrategyMetrics` (frozen): `strategy`, `samples`, `mean_fill_rate`, `collapse_count`
  (runs with < 3 tracks), `mean_transition_validity`, `mean_energy_monotonicity` (`float | None`).
- `EvalReport` (frozen): `tuple[StrategyMetrics, ...]` + a deterministic `render()` to text.
- `evaluate_recommendations(tracks, config) -> EvalReport` — the orchestrator.
- Pure metric helpers, each independent of the code under tuning:
  - `_sample_anchors(tracks, seed, n)` — seeded `random.Random`, deterministic ordering.
  - `_transition_valid(left, right)` — Camelot wheel adjacency + BPM ≤ 3%, defined here.
  - `_fill_rate(ordered, requested_size)`.
  - `_energy_monotonic_fraction(ordered)`.

Placing it under `quality/` mirrors the existing `quality/recommendation_quality.py` seam.

### New thin CLI

`scripts/eval_recommendation.py` — argument parsing + DB load + report print only. Loads tracks
with `TrackRepository(db_path).list_tracks()`, calls `evaluate_recommendations`, prints
`report.render()`. Default `db_path` is the app library; overridable via `--db`. No logic lives
here, so it needs no unit tests beyond a smoke check.

### Reused (PR1)

- `build_recommendation_pool` (relocated to `recommendation/pool.py`, re-exported by presenter).
- `recommend_playlist` (`recommendation/playlist_service.py`).
- `DJControls(start_path=anchor.path)` to anchor each run, mirroring the desktop flow at
  `main_window.py:1482` and `recommendation_worker.py:42`.

### Scorer independence

`_transition_valid` is implemented inside the harness using categorical DJ rules. It deliberately
does NOT call `score_transition` (the tunable scorer) nor `_camelot_compatible` from the presenter
(the module tuned in PR2), so the metric stays an independent oracle.

## Metric definitions

- **Fill rate** = `len(ordered_tracks) / requested_size`, clamped to `[0, 1]`. Collapse =
  `len(ordered_tracks) < 3`.
- **Transition validity** = valid_pairs / total_pairs; a pair is valid iff Camelot-adjacent AND
  `abs(bpm_l - bpm_r) / min(bpm_l, bpm_r) <= 0.03`. Pairs with missing key/BPM count as invalid.
- **Energy monotonicity** (ascending strategies only) = fraction of adjacent pairs with
  `energy_r >= energy_l`; `None` for non-directional strategies.

## PR2: pool-collapse fix

### Root cause

`build_recommendation_pool` splits `remaining_records` into `compatible` (any anchor tag overlap)
and `fallback` (none), concatenating `compatible` ahead of `fallback` before truncating to
`limit`. A BPM/key-feasible track with no shared generic tag is pushed behind tag-overlapping but
BPM-infeasible tracks; the later adjacent-BPM-jump guard in `playlist_service` then drops the
infeasible ones, collapsing the playlist to 1–2 tracks.

### Approach (decided in apply, test-first)

Stop letting the binary tag-overlap partition dominate slot allocation. The unified
`_track_similarity_key` already ranks `(bpm_bucket, key_bucket, -overlap_count, …)`. Candidate fix:
rank the full `remaining_records` by that key (overlap becomes a tiebreak, not a hard partition),
preserving priority/control tracks at the front. Validate with the harness that fill rate rises
without regressing transition validity. Exact form is finalized during the RED test.

### Why not change scoring weights

Out of scope and risk-laden; the collapse is a pool-selection problem, not a scoring problem.

## Safety considerations

- Read-only: no writes to DB, audio, or Serato V2.
- No DSP added.
- `AppState` untouched (harness operates on `TrackRecord` lists).
- Determinism via explicit seed for reproducible reports.

## Test strategy

- Synthetic `TrackRecord` fixtures (no real files) for all metric unit tests.
- A constructed anchor+pool scenario reproducing the collapse for the PR2 RED test.
- Smoke test for the CLI against a temporary SQLite DB built with `TrackRepository`.
