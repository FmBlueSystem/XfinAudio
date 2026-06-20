# Apply progress: quality-manual-overlap

## Status
Applied.

## RED
- `uv run pytest tests/test_recommendation_quality.py::test_build_quality_report_ignores_duplicate_manual_paths_for_overlap -q`
- Failed as expected: `manual_overlap_ratio` was `0.333333` instead of `0.5`.

## Additional architecture finding
Focused import collection exposed eager package-level dependency cycles:

```text
quality -> dj_readiness -> exporting -> playlist/export explainability -> recommendation -> prep_copilot -> quality
```

## GREEN
- Made `xfinaudio.exporting` and `xfinaudio.recommendation` package exports lazy while preserving public exports.
- Updated `_overlap_ratio()` to use distinct manual reference paths for both numerator and denominator.

## Focused evidence
- `uv run pytest tests/test_recommendation_quality.py -q` -> 6 passed.
- `uv run pytest tests/test_recommendation_quality.py tests/test_serato_playlist_export.py tests/test_sequence_optimizer.py -q` -> 26 passed.
- `uv run pyright src/xfinaudio/exporting/__init__.py src/xfinaudio/recommendation/__init__.py src/xfinaudio/quality/recommendation_quality.py tests/test_recommendation_quality.py` -> 0 errors, 0 warnings.
- `uv run ruff check ...` and `uv run ruff format --check ...` -> pass.
