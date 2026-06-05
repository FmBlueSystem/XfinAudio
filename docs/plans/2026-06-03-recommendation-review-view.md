# Recommendation Review View Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an explicit desktop recommendation review view so DJs can inspect ordered tracks, transition component scores, warnings, and quality summary before export.

**Architecture:** Keep this as UI/view rendering over existing recommendation, explanation, and quality report data. Do not change recommendation algorithms or implement export buttons. Add deterministic helpers where useful so behavior is testable without manual UI interaction.

**Tech Stack:** Python 3.11+, PySide6, pytest, ruff, uv.

---

## Non-goals

- No new recommendation algorithms.
- No desktop export workflow implementation.
- No audio mutation, DSP, rendering, or analysis.
- No live Serato writes.
- No large UI redesign.

## Task 1: Recommendation quality summary label

**Files:**
- Modify: `src/xfinaudio/desktop/main_window.py`
- Test: `tests/test_main_window.py`

**Steps:**
1. Write failing tests that after recommendation, the window displays a review summary containing:
   - track count;
   - transition count;
   - average transition score;
   - warning count.
2. Write a failing test that initial state explains no recommendation is ready for review.
3. Run focused tests and confirm RED.
4. Add `review_summary_label` to layout near recommendation table.
5. Add pure helper `format_quality_summary(report)` if useful.
6. Update `recommend_playlist()` to set the review summary from `result.quality_report`.
7. Run focused tests and full suite.

## Task 2: Transition review table

**Files:**
- Modify: `src/xfinaudio/desktop/main_window.py`
- Test: `tests/test_main_window.py`

**Steps:**
1. Write failing tests that after a two-track recommendation, a transition review table has columns:
   - order;
   - from;
   - to;
   - key score;
   - BPM score;
   - energy score;
   - tag score;
   - final score;
   - warnings.
2. Write failing test that warnings are rendered through existing human-readable warning helper.
3. Run focused tests and confirm RED.
4. Add `transition_review_table` with stable headers.
5. Add `show_transition_review(explanation)` to render `PlaylistExplanation.transitions`.
6. Use component score keys defensively; missing score renders empty string.
7. Preserve raw `last_playlist_explanation` data.
8. Run focused tests and full suite.

## Task 3: Review guidance state

**Files:**
- Modify: `src/xfinaudio/desktop/main_window.py`
- Test: `tests/test_main_window.py`

**Steps:**
1. Write failing test that after recommendation, export guidance explicitly tells user to inspect the review table before exporting.
2. Write failing test that recommending with no scanned records leaves review summary/table in empty state.
3. Run focused tests and confirm RED.
4. Update guidance labels/status accordingly.
5. Ensure no export action is introduced.
6. Run focused tests and full suite.

## Task 4: Documentation/backlog/evidence

**Files:**
- Create: `docs/recommendation-review-view.md`
- Modify: `docs/open-source-release-backlog.md`
- Modify: `docs/release-candidate-evidence.md`

**Steps:**
1. Document what the review view shows and what remains out of scope.
2. Mark Desktop UX P1 `Recommendation review view` completed with evidence.
3. Add verification evidence.
4. Run:
   - `uv run pytest -v tests/test_main_window.py`
   - `uv run pytest -v`
   - `uv run ruff check .`
   - `uv run ruff format --check .`
5. Fresh review before claiming done.
