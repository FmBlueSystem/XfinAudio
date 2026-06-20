# Archive Report: Copilot variant shell bridge explicit

Status: archived

## Implementation

- Implementation PR: #190
- Implementation commit on main: 2106d2da462a97d6bc289f52d0ea276b251c33dc
- Issue: #189

## Result

`_on_copilot_variant_applied` is now an explicit `MainWindow` delegator to `PrepCopilotController.on_variant_applied(index)` and is no longer installed through `shell_layout_compat.LEGACY_LAYOUT_METHODS`.

Remaining grafts after this archive:

- `_start_spectral_completion_worker`
- `_cancel_spectral_completion_worker`
- `_on_spectral_progress_updated`
- `_on_spectral_profile_ready`
- `_on_spectral_completion_finished`

## Verification

Implementation verification passed locally before merge:

- `uv run pytest tests/test_main_window_shell_compat.py -q` — 18 passed
- `uv run pytest tests/test_main_window.py -q -k "prep_copilot or copilot_variant or applied_copilot_variant_badge"` — 11 passed
- `uv run pytest -q` — 933 passed
- `uv run pyright src tests` — 0 errors
- `uv run pytest --cov --cov-fail-under=70 -q` — coverage 89.94%
- `uv run ruff check .` — passed
- `uv run ruff format --check .` — passed
- `uv run python scripts/release_gate_check.py --run` — passed

Post-merge main CI:

- GitHub Actions run 27859354425 — Non-audio release gates passed in 1m53s.

## Safety

- No audio mutation.
- No DSP scope expansion.
- No live Serato DB V2 writes.
- No dependency changes.
- No root `build/` or `dist/` artifacts.
