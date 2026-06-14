# Design: Performance Baseline

## Overview

Add deterministic performance baselines for core audio-free workflows so severe regressions can be caught in CI.

## Scenarios

| Operation | Input size | Measured step |
|-----------|------------|---------------|
| Playlist recommendation | 100 tracks | `recommend_playlist(...)` |
| Playlist recommendation | 500 tracks | `recommend_playlist(...)` |
| In-memory export | 500 tracks | `default_exporter_registry().export(...)` for JSON, CSV, M3U |
| Quality report | 500 tracks | `build_quality_report_json(...)` |
| DJ readiness | 500 tracks | `build_dj_readiness_report(...)` |

## Fixture generator

`tests/fixtures/performance_tracks.py` provides `make_complete_tracks(count)` returning a list of `TrackRecord` objects with deterministic metadata:

- Incremental titles/artists.
- Rotating Camelot keys and BPM values.
- Energy levels within 1-10.
- `metadata_status="complete"`.

## Measurement

- Use `time.perf_counter()` around a single execution.
- Thresholds are generous (e.g. 2s for 500-track recommendation) to avoid flakiness on shared CI runners.
- Tests fail only if the threshold is exceeded, making them a regression guard rather than a strict benchmark.

## Reporter script

`scripts/performance_baseline.py` runs the scenarios and prints:

```markdown
| Operation | Tracks | Elapsed (s) | Threshold (s) | Status |
|-----------|--------|-------------|---------------|--------|
| recommend_playlist | 500 | 0.45 | 2.0 | pass |
```

## Tests

- `tests/test_performance_baseline.py` contains the same scenarios with assertions.
- Fixtures are reused between tests and the reporter script.

## Safety

- No file I/O during measurement.
- No real audio processing.
- Deterministic fixtures produce stable measurements.
