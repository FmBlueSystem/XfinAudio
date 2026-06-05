# Release Readiness Smoke and Runbook Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a reproducible post-MVP release readiness smoke workflow, user runbook, and open-source release backlog for XfinAudio.

**Architecture:** Keep this as verification/documentation, not new product functionality. Add a small smoke script that exercises existing application/domain services without requiring real audio files or mutating audio. Document manual desktop QA separately.

**Tech Stack:** Python 3.11+, uv, pytest, ruff, PySide6, SQLite, pydantic.

---

## Non-goals

- No new recommendation algorithms.
- No DSP, audio analysis, or audio mutation.
- No live Serato library write.
- No packaging installer yet.
- No large UI redesign.

## Task 1: Automated smoke script

**Files:**
- Create: `scripts/smoke_release_readiness.py`
- Test: `tests/test_release_smoke.py`

**Steps:**
1. Write a failing test that runs the smoke script in a subprocess and expects success plus a concise checklist in stdout.
2. Run focused test and confirm RED.
3. Implement the script to:
   - create a temp app DB;
   - build deterministic complete `TrackRecord` fixtures;
   - save/list records through `TrackRepository`;
   - run `PlaylistWorkflowService.recommend(...)`;
   - build JSON/CSV/M3U export strings through the exporter registry;
   - build quality report JSON;
   - build a dry-run Serato crate export plan without writing;
   - print pass lines for each step.
4. Ensure it writes only temp DB files and no audio files.
5. Run focused test and full suite.

## Task 2: Manual desktop smoke checklist

**Files:**
- Create: `docs/release-readiness-smoke.md`

**Steps:**
1. Document exact commands:
   - `uv sync`
   - `uv run pytest -v`
   - `uv run ruff check .`
   - `uv run ruff format --check .`
   - `uv run python scripts/smoke_release_readiness.py`
   - `uv run xfinaudio`
2. Document manual desktop QA:
   - launch app;
   - choose folder with Mixed In Key processed audio;
   - scan;
   - verify complete/incomplete counts;
   - recommend playlist;
   - verify explainability scores/warnings;
   - export safely outside audio folders;
   - do not use live Serato writes; use dry-run/fixture only.
3. Document expected output and known limitations.

## Task 3: Open-source release backlog document

**Files:**
- Create: `docs/open-source-release-backlog.md`

**Steps:**
1. Create backlog sections:
   - Release candidate blockers;
   - Product polish;
   - Serato compatibility;
   - Settings/persistence;
   - Desktop UX;
   - QA/fixtures;
   - Packaging/distribution.
2. Prioritize with P0/P1/P2.
3. Include acceptance criteria per backlog item.
4. Keep it concise and actionable.

## Task 4: Verification

**Steps:**
1. Run:
   - `uv run python scripts/smoke_release_readiness.py`
   - `uv run pytest -v`
   - `uv run ruff check .`
   - `uv run ruff format --check .`
2. Run LSP diagnostics on new script/test if available.
3. Fresh review the docs/script before claiming done.
