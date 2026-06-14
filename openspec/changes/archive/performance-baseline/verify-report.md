# Verify Report: Performance Baseline

## Verification commands

All commands were run in order and passed.

```bash
uv run pytest tests/test_performance_baseline.py -v
uv run python scripts/performance_baseline.py
uv run pytest -q
uv run pyright src tests
uv run pytest --cov --cov-fail-under=70 -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/release_gate_check.py --run
```

## Results

| Gate | Status | Evidence |
|------|--------|----------|
| pytest focused | passed | 5 passed |
| reporter script | passed | all scenarios pass |
| pytest full | passed | 721 passed |
| pyright | passed | 0 errors, 0 warnings, 0 informations |
| pytest-cov | passed | 88.68% coverage (threshold 70%) |
| ruff check | passed | All checks passed! |
| ruff format | passed | 169 files already formatted |
| release_gate_check.py --run | passed | All automated gates passed |

## Requirement-by-requirement evidence

1. **Recommendation baseline**: `test_recommend_playlist_performance` measures 50 and 100 track recommendations against 2s and 4s thresholds.
2. **Export baseline**: `test_export_playlist_performance` measures JSON/CSV/M3U in-memory export of a 100-track recommendation.
3. **Quality report baseline**: `test_quality_report_performance` measures quality report JSON serialization.
4. **DJ readiness baseline**: `test_dj_readiness_report_performance` measures DJ readiness report generation.
5. **Reporter script**: `scripts/performance_baseline.py` runs the same scenarios and prints a Markdown table with elapsed times and pass/fail status.
6. **Fixtures**: `tests/fixtures/performance_tracks.py` provides deterministic complete tracks.

## Limitations

- Baselines are audio-free; real-world scan performance is not measured.
- Thresholds are calibrated on current CI hardware and may need adjustment for slower runners.
