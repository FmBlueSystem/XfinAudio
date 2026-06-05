# HELP-8 Release Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Harden XfinAudio for MVP release readiness with versioned settings, safe SQLite schema handling, typed errors/logging, registries, and a thin UI workflow layer.

**Architecture:** Keep domain logic pure and outside the UI. Add small application/config/registry seams without changing current product behavior. Preserve existing defaults exactly while making policy configurable and testable.

**Tech Stack:** Python 3.11+, PySide6, SQLite, pydantic, pytest, ruff, uv, standard-library logging/pathlib/sqlite3.

---

## Non-goals

- No DSP, key/BPM detection, beat tracking, audio rendering/mixing, or audio mutation.
- No large UI redesign.
- No live Serato workflow beyond HELP-7 safe artifact primitives.
- No external config file persistence unless tests need temp files; pydantic settings model is enough for MVP hardening.
- No speculative analytics/history system.

## Task 1: Safe SQLite schema version handling

**Files:**
- Modify: `src/xfinaudio/library/track_repository.py`
- Test: `tests/test_track_repository.py`

**Steps:**
1. Write failing tests:
   - new DB initializes `PRAGMA user_version` to current schema version;
   - DB with future `user_version` raises a typed schema error and does not reset version;
   - DB with current version remains usable.
2. Run focused test and confirm RED.
3. Add `DatabaseSchemaError` / `UnsupportedDatabaseVersionError`.
4. Change initialization to read `PRAGMA user_version` before schema writes:
   - `0` creates v1 schema and sets version;
   - current version is no-op/ensure table only;
   - future version rejects without mutation.
5. Keep repository API compatible.
6. Run focused test and full suite.

## Task 2: Versioned app settings model

**Files:**
- Create: `src/xfinaudio/config/__init__.py`
- Create: `src/xfinaudio/config/settings.py`
- Test: `tests/test_settings.py`

**Steps:**
1. Write failing tests for default settings:
   - `settings_version == 1`;
   - scan supported extensions match current behavior;
   - optimizer exact limit remains `20`;
   - default scoring weights match current defaults;
   - unknown future settings version is rejected.
2. Run focused test and confirm RED.
3. Implement pydantic settings models:
   - `AppSettings`;
   - `ScanSettings`;
   - `OptimizerSettings`;
   - `ScoringSettings` using existing `ScoringWeights` or equivalent validated model.
4. Ensure non-negative scoring validation remains enforced.
5. Run focused test and full suite.

## Task 3: Configurable scoring thresholds without behavior change

**Files:**
- Modify: `src/xfinaudio/recommendation/scoring.py`
- Test: `tests/test_transition_scoring.py`

**Steps:**
1. Write failing tests proving custom BPM/energy thresholds alter scores deterministically.
2. Run focused test and confirm RED.
3. Add small pydantic config models:
   - `ThresholdScore(max_delta, score)`;
   - `TransitionScoringConfig(weights, bpm_thresholds, energy_thresholds, required_fields)`.
4. Keep `DEFAULT_WEIGHTS` and current public calls working.
5. Let `score_transition(..., config=None)` use current default thresholds when no config is supplied.
6. Run focused test and full suite.

## Task 4: Strategy registry seam

**Files:**
- Modify: `src/xfinaudio/recommendation/strategies.py`
- Modify: `src/xfinaudio/recommendation/playlist_service.py`
- Test: `tests/test_playlist_strategies.py`
- Test: `tests/test_playlist_service.py`

**Steps:**
1. Write failing tests for `StrategyRegistry`:
   - default registry lists all current strategies;
   - lookup returns same existing profiles;
   - duplicate registration rejects;
   - unknown strategy rejects.
2. Run focused tests and confirm RED.
3. Implement `StrategyRegistry` and `default_strategy_registry()`.
4. Keep existing `available_strategies()` and `get_strategy()` wrappers for compatibility.
5. Allow `recommend_playlist(..., strategy_registry=None)` to use injected registry.
6. Run focused tests and full suite.

## Task 5: Exporter registry seam

**Files:**
- Modify: `src/xfinaudio/exporting/playlist_exporters.py`
- Test: `tests/test_playlist_exporters.py`

**Steps:**
1. Write failing tests for registry lookup/listing:
   - default formats are `json`, `csv`, `m3u`;
   - unknown format rejects;
   - exporting through registry matches existing function output.
2. Run focused test and confirm RED.
3. Add `PlaylistExporter` pydantic/model or dataclass with `name`, `extension`, `media_type`, and callable.
4. Add `ExporterRegistry` and `default_exporter_registry()`.
5. Keep existing export/write functions unchanged.
6. Run focused test and full suite.

## Task 6: Logging and typed scan errors without breaking skip behavior

**Files:**
- Modify: `src/xfinaudio/library/scan_service.py`
- Test: `tests/test_scan_service.py`

**Steps:**
1. Write failing test using `caplog` proving unreadable supported files are skipped and logged without raw metadata.
2. Run focused test and confirm RED.
3. Add module logger.
4. In tag-reader exception path, log warning with file path and exception class/message.
5. Keep existing skip behavior and result counts unchanged.
6. Run focused test and full suite.

## Task 7: Application workflow service to remove UI business sequencing

**Files:**
- Create: `src/xfinaudio/application/__init__.py`
- Create: `src/xfinaudio/application/playlist_workflow.py`
- Modify: `src/xfinaudio/desktop/main_window.py`
- Test: `tests/test_playlist_workflow.py`
- Test: `tests/test_main_window.py`

**Steps:**
1. Write failing tests for `PlaylistWorkflowService.scan_folder(folder)`:
   - returns records plus complete/incomplete counts;
   - persists records through repository.
2. Write failing tests for `PlaylistWorkflowService.recommend(records, strategy_name)`:
   - returns recommendation;
   - returns playlist explanation;
   - returns quality report.
3. Run focused workflow tests and confirm RED.
4. Implement pydantic result models `ScanWorkflowResult` and `RecommendationWorkflowResult`.
5. Move scan/recommend/explain/quality sequencing into workflow service.
6. Update `MainWindow` to call workflow service and only render returned data.
7. Preserve existing UI tests and behavior.
8. Run focused tests and full suite.

## Task 8: Quality report export integration

**Files:**
- Modify: `src/xfinaudio/exporting/playlist_exporters.py`
- Test: `tests/test_playlist_exporters.py`

**Steps:**
1. Write failing test for `export_quality_report_json(report)` deterministic output.
2. Run focused test and confirm RED.
3. Implement JSON export for `RecommendationQualityReport`.
4. Register quality report exporter only if it does not confuse playlist exporter registry; otherwise keep a separate function.
5. Run focused test and full suite.

## Task 9: Documentation and verification

**Files:**
- Create: `docs/help-8-release-hardening.md`

**Steps:**
1. Document:
   - schema version behavior;
   - settings schema v1;
   - registry seams;
   - logging/error behavior;
   - application workflow service;
   - non-goals and remaining backlog.
2. Run:
   - `uv run pytest -v`
   - `uv run ruff check .`
   - `uv run ruff format --check .`
3. Run LSP diagnostics on changed source files.
4. Run fresh review before accepting HELP-8.
5. Update Jira HELP-8 with verification evidence and transition only after no blockers.
