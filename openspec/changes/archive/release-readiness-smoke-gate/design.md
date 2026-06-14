# Design: Release Readiness Smoke Gate

## Overview

The release readiness smoke is a deterministic, audio-free script that exercises the core application service seams:

- SQLite persistence (`TrackRepository`)
- Recommendation workflow (`PlaylistWorkflowService`)
- Playlist exporters (`ExporterRegistry`)
- Quality report (`build_quality_report`)
- DJ readiness (`build_dj_readiness_report` with a dry-run Serato plan)

## Architecture

```text
scripts/smoke_release_readiness.py
├── StaticScanService  (returns fixture TrackRecords)
├── TrackRepository(temp_db)
├── PlaylistWorkflowService.recommend(...)
├── default_exporter_registry().export(json/csv/m3u)
├── export_quality_report_json(...)
└── build_dj_readiness_report(..., serato_plan=dry_run_plan)
```

The Serato plan is built with `plan_serato_crate_export` against a temporary `_Serato_/Subcrates` folder. The plan is never executed, so no crate file is written to a live library.

## Gate integration

`scripts/release_gate_check.py` adds:

```python
CommandGate(
    "release readiness smoke",
    ["uv", "run", "python", "scripts/smoke_release_readiness.py"],
)
```

The gate runs after lint/format and before publication-hygiene gates.

## Test-first checklist

1. Update `tests/test_release_smoke.py` with the expected DJ readiness pass line; confirm RED.
2. Implement the DJ readiness step in the smoke script; confirm GREEN.
3. Update `tests/test_release_gate_check.py` gate list; confirm RED.
4. Register the gate; confirm GREEN.

## Safety constraints

- Only temp directories under `tempfile.TemporaryDirectory`.
- No real audio file reads.
- Serato plan is preview-only (`will_write=False`).
