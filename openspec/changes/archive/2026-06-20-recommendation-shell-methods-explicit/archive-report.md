# Archive Report: Recommendation shell methods explicit

Status: archived

## Implementation

- Implementation PR: #186
- Implementation commit on main: 80dc28a573c0624d733b73067601db54acc8ded4
- Issue: #185

## Result

The eight Recommendation shell methods are now explicit `MainWindow` delegators and are no longer installed through `shell_layout_compat.LEGACY_LAYOUT_METHODS`.

Removed from the graft map:

- `recommend_playlist`
- `_begin_recommendation_state`
- `_end_recommendation_state`
- `_start_recommendation_worker`
- `_finish_recommendation`
- `_fail_recommendation`
- `_populate_dj_readiness_table`
- `_on_recommend_requested`

Remaining grafts after this archive:

- `_on_copilot_variant_applied`
- `_start_spectral_completion_worker`
- `_cancel_spectral_completion_worker`
- `_on_spectral_progress_updated`
- `_on_spectral_profile_ready`
- `_on_spectral_completion_finished`

## Verification

Implementation verification passed locally before merge:

- `uv run pytest tests/test_main_window_shell_compat.py -q` — 18 passed
- focused Recommendation regression tests — 4 passed
- `uv run pytest -q` — 933 passed
- `uv run pyright src tests` — 0 errors
- `uv run pytest --cov --cov-fail-under=70 -q` — coverage 89.95%
- `uv run ruff check .` — passed
- `uv run ruff format --check .` — passed
- `uv run python scripts/release_gate_check.py --run` — passed

Post-merge main CI:

- GitHub Actions run 27858863273 — Non-audio release gates passed in 1m59s.

## Safety

- No audio mutation.
- No DSP scope expansion.
- No live Serato DB V2 writes.
- No dependency changes.
- No root `build/` or `dist/` artifacts.
