# HELP-7 Explainability, Exports, Serato Crate, and Quality Validation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add explainable playlist output, deterministic JSON/CSV/M3U exports, a safe Serato crate export spike, and recommendation quality validation.

**Architecture:** Keep export and quality modules pure Python under `src/xfinaudio/exporting/` and `src/xfinaudio/quality/`. Serato crate support is limited to deterministic crate artifact generation plus dry-run/backup/confirm safety; never mutate audio files. UI integration is minimal and should delegate to services.

**Tech Stack:** Python 3.11+, pydantic, pytest, ruff, uv, standard-library csv/json/pathlib/shutil.

---

## Serato research basis

Open-source reverse-engineering references (Mixxx wiki, pyserato, python-serato-crates, parser snippets) agree on these points:

- Serato crates live under `_Serato_/Subcrates/` and are named `<crate>.crate`.
- `.crate` files use TLV records: 4-byte ASCII tag, 4-byte big-endian length, payload bytes.
- `vrsn` is UTF-16BE text, commonly `1.0/Serato ScratchLive Crate`.
- Track entries are `otrk` records containing nested records.
- Crate track path tag is `ptrk` and stores a path relative to the crate drive/root.
- Paths/strings are UTF-16BE in documented implementations.

## Non-goals

- No writes into a live Serato library without explicit confirm flag and backup path.
- No Serato database V2 mutation.
- No audio file mutation.
- No DSP, audio rendering, key/BPM detection, beat tracking, or mixing.
- No polished export UI beyond minimal wiring if safe.

## Task 1: Transition explainability report

**Files:**
- Create: `src/xfinaudio/exporting/explainability.py`
- Test: `tests/test_explainability.py`

**Steps:**
1. Write failing tests for a report that includes each transition's left/right tracks, key/BPM/energy/tag/final scores, warnings, and explanations.
2. Run focused test and confirm RED.
3. Implement pydantic models `TransitionExplanation` and `PlaylistExplanation` plus `build_playlist_explanation(recommendation)`.
4. Ensure output is JSON-serializable and deterministic.
5. Run focused test and full suite.

## Task 2: JSON/CSV/M3U exporters

**Files:**
- Create: `src/xfinaudio/exporting/playlist_exporters.py`
- Test: `tests/test_playlist_exporters.py`

**Steps:**
1. Write failing tests for deterministic JSON export including ordered tracks and transition explanations.
2. Write failing tests for CSV export with stable columns: order, path, title, artist, bpm, camelot_key, energy_level, status.
3. Write failing tests for M3U export preserving track order using file paths.
4. Run focused tests and confirm RED.
5. Implement `export_playlist_json()`, `export_playlist_csv()`, `export_playlist_m3u()` returning strings and optional `write_*` helpers that write only caller-provided export files.
6. Run focused test and full suite.

## Task 3: Serato crate artifact and safety flow

**Files:**
- Create: `src/xfinaudio/exporting/serato_crate.py`
- Test: `tests/test_serato_crate.py`

**Steps:**
1. Write failing tests for TLV encoding:
   - `vrsn` UTF-16BE record;
   - `otrk` record with nested `ptrk` UTF-16BE relative path;
   - order preserved.
2. Write failing tests for path validation: crate paths must be relative, non-empty, and not escape via `..`.
3. Write failing tests for `SeratoExportPlan` dry-run preview that lists target path, backup path, track count, and no writes.
4. Write failing tests for confirmed write that creates backup if target exists, then writes crate bytes to a caller-provided target under temp dir.
5. Run focused tests and confirm RED.
6. Implement TLV encoder and safety wrapper:
   - `build_serato_crate_bytes(relative_paths)`;
   - `plan_serato_crate_export(crate_name, relative_paths, serato_root)`;
   - `write_serato_crate(plan, confirm=False)` where `confirm=False` raises or returns dry-run without writing.
7. Do not discover or write real Serato library locations automatically in this stage.
8. Run focused test and full suite.

## Task 4: Recommendation quality validation

**Files:**
- Create: `src/xfinaudio/quality/recommendation_quality.py`
- Test: `tests/test_recommendation_quality.py`

**Steps:**
1. Write failing tests for quality report metrics: track count, transition count, average transition score, BPM jumps, energy jumps, warning count.
2. Write failing tests comparing generated playlist against a manual path sequence with overlap ratio and order-match prefix count.
3. Run focused tests and confirm RED.
4. Implement `build_quality_report(recommendation, manual_paths=None)`.
5. Run focused test and full suite.

## Task 5: Minimal desktop export/explainability integration

**Files:**
- Modify: `src/xfinaudio/desktop/main_window.py`
- Test: `tests/test_main_window.py`

**Steps:**
1. Write failing smoke test that after recommendation, transition explanation status/table data is available for display.
2. Avoid real file dialogs for export in tests; UI can expose data/service hooks but not full save UX if too large.
3. Implement minimal display of transition final score/warnings in recommendation table or status.
4. Run focused tests and full suite.

## Task 6: Documentation and verification

**Files:**
- Create: `docs/help-7-explainability-exports-serato-quality.md`

**Steps:**
1. Document exporters, Serato crate research/safety policy, quality metrics, non-goals, and current limitations.
2. Run:
   - `uv run pytest -v`
   - `uv run ruff check .`
   - `uv run ruff format --check .`
3. Run fresh review before accepting HELP-7.
4. Update Jira HELP-7 with evidence and transition to done only after review has no blockers.
