# Modular Boundary Inventory Apply Progress

## Status

Complete.

## Applied Work

- Added `docs/architecture/functional-inventory.md` with module ownership, current files, target owners, tests, and next separation slices.
- Moved pure recommendation candidate-pool policy to `src/xfinaudio/recommendation/candidate_pool.py`.
- Kept `src/xfinaudio/desktop/recommendation_presenter.py` as a compatibility wrapper.
- Updated desktop imports in `main_window.py` and `recommendation_service.py` to consume the non-UI recommendation module.
- Added `StrategyRegistry.resolve_name()` and `resolve_strategy_name()` so internal strategy names and built-in display labels resolve through a tested domain boundary.
- Updated Prep Copilot desktop controller to prefer combo item data before display text.
- Fixed a Ruff E402 import-order issue in `src/xfinaudio/desktop/spectral_completion_worker.py` while running the full gate.
- Formatted `src/xfinaudio/audio/spectral_profile.py`, `tests/integration_flow.py`, and `tests/test_main_window.py` because the full format gate reported them as non-compliant.

## TDD Evidence

RED command:

```bash
uv run pytest tests/test_recommendation_presenter.py tests/test_playlist_strategies.py -q
```

Expected RED result observed:

- `ModuleNotFoundError: No module named 'xfinaudio.recommendation.candidate_pool'`
- `ImportError: cannot import name 'resolve_strategy_name'`

GREEN command:

```bash
uv run pytest tests/test_recommendation_presenter.py tests/test_playlist_strategies.py -q
```

Observed GREEN result:

- `35 passed in 0.47s`
