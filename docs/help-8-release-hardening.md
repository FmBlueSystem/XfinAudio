# HELP-8 Release Hardening

HELP-8 adds release-readiness seams without changing the current product defaults or behavior.

## SQLite schema version behavior

`TrackRepository` now treats the SQLite `PRAGMA user_version` as the application-owned schema version.

- New empty databases (`user_version == 0` with no existing `tracks` table) initialize the v1 `tracks` table and set `user_version` to `1`.
- Unversioned databases that already contain a `tracks` table are rejected with `DatabaseSchemaError` before changing `user_version`, because they need an explicit migration instead of silent stamping.
- Current v1 databases remain usable and ensure the expected table exists.
- Future databases (`user_version > 1`) raise `UnsupportedDatabaseVersionError` before any schema writes, so newer files are not silently downgraded or reset.

## Settings schema v1

`xfinaudio.config.settings.AppSettings` is the versioned root settings model.

Defaults intentionally match existing behavior:

- `settings_version == 1`
- scan extensions: `.aif`, `.aiff`, `.flac`, `.m4a`, `.mp3`, `.wav`
- optimizer exact limit: `20`
- scoring weights: harmonic `0.40`, BPM `0.25`, energy `0.25`, tags `0.10`

Unknown future settings versions are rejected. Scoring weight validation remains non-negative with positive total weight.

## Scoring configurability

`TransitionScoringConfig` adds configurable BPM and energy threshold tables while preserving default scores:

- BPM: `<=2% -> 1.0`, `<=4% -> 0.75`, `<=8% -> 0.5`, otherwise `0.0`
- energy delta: `<=1 -> 1.0`, `<=2 -> 0.7`, `<=3 -> 0.4`, otherwise `0.0`

Existing calls to `score_transition(...)` and existing `ScoringWeights` behavior remain compatible.

## Registry seams

Two extension seams were added for packaging and future controlled expansion:

- `StrategyRegistry` with `default_strategy_registry()` for playlist strategy lookup, including custom in-process `PlaylistStrategy` profiles.
- `ExporterRegistry` with `default_exporter_registry()` for playlist exporters (`json`, `csv`, `m3u`).

Compatibility wrappers such as `available_strategies()`, `get_strategy()`, and existing export functions are unchanged.

## Logging and scan errors

Supported audio files that fail tag reading are still skipped, preserving existing scan semantics. The scanner now logs a warning containing:

- file path;
- exception class;
- exception message.

The warning does not log raw metadata.

## Application workflow service

`PlaylistWorkflowService` centralizes application sequencing outside the UI:

- `scan_folder(folder)` scans, persists, and returns records plus complete/incomplete counts.
- `recommend(records, strategy_name)` returns the recommendation, playlist explanation, and quality report.

`MainWindow` now renders returned workflow data instead of building recommendation/explanation/quality sequencing directly.

## Quality report JSON export

`export_quality_report_json(report)` exports `RecommendationQualityReport` as deterministic, sorted, indented JSON.

## Non-goals preserved

HELP-8 does not add DSP, C++, key/BPM detection, beat tracking, audio rendering/mixing, audio mutation, Serato DB V2 mutation, or unsafe live Serato writes.

## Remaining backlog

- External persisted settings files are still intentionally out of scope.
- Registry-backed plugin loading is not implemented; registries are in-process seams only.
- SQLite migrations beyond v1 are not implemented; future versions are rejected safely.
