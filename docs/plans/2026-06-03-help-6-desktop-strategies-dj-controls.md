# HELP-6 Desktop Playlist Strategies and DJ Controls Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add product-level playlist strategy selection and DJ control constraints on top of the HELP-5 recommender, then expose a minimal desktop workflow.

**Architecture:** Keep recommendation policy and control state in pure Python modules under `src/xfinaudio/recommendation/`. Keep PySide6 UI as a thin wiring layer that displays scanned tracks, lets the DJ choose intent/controls, and renders a recommended order. Do not implement export, Serato, DSP, or audio mutation.

**Tech Stack:** Python 3.11+, PySide6, pydantic, pytest, ruff, uv.

---

## Non-goals

- No DSP, key detection, BPM detection, beat tracking, rendering, mixing, Serato, or exports.
- No persistent settings yet beyond existing SQLite scan persistence.
- No drag-and-drop UI polish; minimal controls are acceptable if domain tests prove behavior.
- No background worker unless needed for a safe smoke path; document sync limitation if kept.

## Task 1: Strategy profiles

**Files:**
- Create: `src/xfinaudio/recommendation/strategies.py`
- Test: `tests/test_playlist_strategies.py`

**Steps:**
1. Write failing tests for available strategy names: `harmonic_journey`, `warmup`, `build`, `peak_time`, `chill`, `same_energy`, `same_vibe`.
2. Write failing tests that strategy profiles expose scoring weights and eligibility/sort hints:
   - warmup prefers low/mid energy;
   - build prefers ascending energy;
   - peak_time prefers high energy;
   - chill prefers lower energy/BPM;
   - same_energy uses energy tolerance;
   - same_vibe requires tags/genre and degrades when unavailable;
   - harmonic_journey emphasizes harmonic weight.
3. Run focused tests and confirm RED.
4. Implement `PlaylistStrategy`, `StrategyName`, `get_strategy(name)`, `available_strategies()`.
5. Run focused tests and full suite.

## Task 2: DJ control constraints

**Files:**
- Create: `src/xfinaudio/recommendation/controls.py`
- Test: `tests/test_dj_controls.py`

**Steps:**
1. Write failing tests for `DJControls` validation:
   - locked paths are preserved;
   - excluded paths are removed;
   - start/end paths are validated;
   - manual order paths are preserved first/in order;
   - invalid overlap between excluded and locked/start/end raises.
2. Run focused tests and confirm RED.
3. Implement pydantic `DJControls` and `apply_controls(tracks, controls)` returning candidate tracks plus start/end/manual prefix metadata.
4. Run focused tests and full suite.

## Task 3: Recommendation service

**Files:**
- Create: `src/xfinaudio/recommendation/playlist_service.py`
- Test: `tests/test_playlist_service.py`

**Steps:**
1. Write failing tests for `recommend_playlist(tracks, strategy_name, controls=None, weights_override=None)`:
   - excludes incomplete tracks;
   - applies strategy filtering/order hints;
   - respects excluded/start/end controls;
   - preserves manual order prefix where feasible;
   - uses custom weights override;
   - same_vibe degrades gracefully when tags are unavailable.
2. Run focused tests and confirm RED.
3. Implement service by combining strategy profile + controls + HELP-5 `recommend_sequence`.
4. Return a pydantic `PlaylistRecommendation` containing ordered tracks, transition scores, strategy, warnings, and applied_controls summary.
5. Run focused tests and full suite.

## Task 4: Minimal desktop integration

**Files:**
- Modify: `src/xfinaudio/desktop/main_window.py`
- Test: `tests/test_main_window.py`

**Steps:**
1. Write failing UI smoke tests for strategy dropdown, recommend button, generated playlist table/status, and basic use of scanned records.
2. Run focused tests and confirm RED.
3. Add thin UI widgets:
   - strategy combo;
   - recommend playlist button;
   - recommendation table;
   - status text showing chosen strategy and count.
4. Keep business logic in `playlist_service.py`; UI only passes scanned records and displays results.
5. Run focused tests and full suite.

## Task 5: Documentation and verification

**Files:**
- Create: `docs/help-6-desktop-strategies-dj-controls.md`

**Steps:**
1. Document supported strategies, controls, current UI limitations, and non-goals.
2. Run:
   - `uv run pytest -v`
   - `uv run ruff check .`
   - `uv run ruff format --check .`
3. Run fresh review before accepting HELP-6.
4. Update Jira HELP-6 with evidence and transition to done only after review has no blockers.
