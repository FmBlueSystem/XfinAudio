# Apply Progress: Phase 1 - Space Utilization

## Completed

- Removed `setMaximumHeight(190)` constraint from `tracks_table`
- Changed `setMinimumHeight(132)` to `setMinimumHeight(400)`
- Changed `setSizePolicy(Expanding, Fixed)` to `setSizePolicy(Expanding, Expanding)`
- Removed unused constants `_COMPACT_LIBRARY_TABLE_MAX_HEIGHT` and `_COMPACT_LIBRARY_TABLE_MIN_HEIGHT` from theme.py
- Updated test to verify minimumHeight >= 400 instead of maximumHeight <= 190

## Verification

- `uv run pytest -q` -> 815 passed
- `uv run pyright src tests` -> 0 errors
- `uv run pytest --cov --cov-fail-under=70 -q` -> 88.62% coverage
- `uv run ruff check .` -> pass
- `uv run ruff format --check .` -> pass
