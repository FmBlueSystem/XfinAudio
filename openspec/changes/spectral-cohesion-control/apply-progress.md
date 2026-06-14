# Apply Progress: Spectral Cohesion Control

## Completed

- Implemented `spectral_cohesion` in `TransitionScoringConfig` with range validation.
- Added `_effective_weights()` to scale spectral weight by cohesion.
- Added `_spectral_color_penalty()` for different dominant colors.
- Threaded `TransitionScoringConfig` through optimizer, playlist service, workflow service, and controllers.
- Added "Same Color" strategy.
- Added Build Playlist slider, label, signal, and accessor.
- Persisted slider value in `AppSettings.scoring.spectral_cohesion`.
- Added unit tests for cohesion penalty, weight boost, range validation, and strategy presence.
- Updated existing tests for new strategy count and combo count.

## Verification status

- `uv run pytest -q`: PASS — 778 tests passed
- `uv run pyright src tests`: PASS — 0 errors
- `uv run pytest --cov --cov-fail-under=70 -q`: PASS
- `uv run ruff check .`: PASS
- `uv run ruff format --check .`: PASS
- `uv run python scripts/release_gate_check.py --run`: PASS

## Notes

- Scoring default remains `spectral_cohesion=0.0` for backward compatibility; app default is `0.5` via settings.
- Removed an orphaned `assets/.DS_Store` that broke publication artifact hygiene.
