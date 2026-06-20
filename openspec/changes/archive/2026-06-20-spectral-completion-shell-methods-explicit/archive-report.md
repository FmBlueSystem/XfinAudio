# Archive Report: Spectral completion shell methods explicit

Status: archived

## Implementation

- Implementation PR: #194
- Implementation commit on main: cbfa7dc3d7c50cf91009e6a70d1a9e10214379ea
- Issue: #193

## Result

The five spectral completion lifecycle methods are now explicit `MainWindow` delegators to `LibraryController` and are no longer installed through `shell_layout_compat.LEGACY_LAYOUT_METHODS`.

Removed from the graft map:

- `_start_spectral_completion_worker`
- `_cancel_spectral_completion_worker`
- `_on_spectral_progress_updated`
- `_on_spectral_profile_ready`
- `_on_spectral_completion_finished`

`LEGACY_LAYOUT_METHODS` now has 0 methods. `install_legacy_layout_methods()` remains as a stable no-op for a final safe-removal slice.

## Verification

Implementation verification passed locally before merge:

- `uv run pytest tests/test_main_window_shell_compat.py -q` — 19 passed
- focused spectral behavior tests — passed
- `uv run pytest -q` — 934 passed
- `uv run pyright src tests` — 0 errors
- `uv run pytest --cov --cov-fail-under=70 -q` — coverage 89.84%
- `uv run ruff check .` — passed
- `uv run ruff format --check .` — passed
- `uv run python scripts/release_gate_check.py --run` — passed

Post-merge main CI:

- GitHub Actions run 27859875541 — Non-audio release gates passed in 2m12s.

## Safety

- No audio mutation.
- No DSP scope expansion.
- No live Serato DB V2 writes.
- No dependency changes.
- No root `build/` or `dist/` artifacts.
