# UI Empty States and Warning Clarity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve the desktop MVP's usability with clear empty-state guidance and human-readable recommendation warnings without changing recommendation algorithms.

**Architecture:** Keep this as thin UI/view-model polish. Add small pure helpers for warning text mapping so tests can verify clarity without needing a full UI redesign. Preserve current scan/recommend behavior and product constraints.

**Tech Stack:** Python 3.11+, PySide6, pytest, ruff, uv.

---

## Non-goals

- No new recommendation algorithms.
- No export workflow implementation in desktop.
- No large UI redesign.
- No DSP, audio analysis, audio rendering, audio mutation, or live Serato writes.

## Task 1: Empty-state guidance labels

**Files:**
- Modify: `src/xfinaudio/desktop/main_window.py`
- Test: `tests/test_main_window.py`

**Steps:**
1. Write failing tests that a newly constructed `MainWindow` displays guidance text for:
   - choosing a Mixed In Key processed folder;
   - scanning before recommending;
   - safe export/review reminder.
2. Run focused test and confirm RED.
3. Add QLabel widgets such as `library_guidance_label`, `recommendation_guidance_label`, and `export_guidance_label`.
4. Keep table/status widgets unchanged.
5. Update scan/recommend methods to adjust guidance after successful scan/recommend:
   - after scan: guide user to choose a strategy and recommend;
   - after recommend: guide user to review scores/warnings before export.
6. Run focused test and full suite.

## Task 2: Human-readable warning clarity helper

**Files:**
- Modify: `src/xfinaudio/desktop/main_window.py`
- Test: `tests/test_main_window.py`

**Steps:**
1. Write failing tests for `format_recommendation_warning(raw_warning)` or similar pure helper:
   - incomplete metadata warnings become user-friendly;
   - invalid Camelot key warnings explain Mixed In Key metadata issue;
   - empty warnings stay empty;
   - unknown warnings are preserved but prefixed as a review note.
2. Run focused test and confirm RED.
3. Implement helper near UI code or in a small view helper section.
4. Use helper when rendering recommendation warning cells.
5. Keep raw domain warnings available in `last_playlist_explanation`.
6. Run focused test and full suite.

## Task 3: Documentation and backlog evidence

**Files:**
- Create: `docs/ui-empty-states-warning-clarity.md`
- Modify: `docs/open-source-release-backlog.md`
- Modify: `docs/release-candidate-evidence.md`

**Steps:**
1. Document what changed and what remains out of scope.
2. Mark Product polish P1 empty-state guidance and warning clarity as completed/partially completed with this evidence.
3. Add verification output to release candidate evidence.
4. Run:
   - `uv run pytest -v tests/test_main_window.py`
   - `uv run pytest -v`
   - `uv run ruff check .`
   - `uv run ruff format --check .`
5. Fresh review before claiming done.
