# Scan Progress and Cancel Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add scan progress feedback and a non-destructive cooperative cancel path for long metadata scans.

**Architecture:** Extend the read-only scan service with progress callbacks and cancellation tokens. Keep UI wiring thin and avoid threads for this stage; cancellation is cooperative and prevents persistence of partial scan results. Future background workers can reuse the same seams.

**Tech Stack:** Python 3.11+, PySide6, pydantic, pytest, ruff, uv.

---

## Non-goals

- No background worker/threading in this slice.
- No progress bar widget unless needed; status/label feedback is enough.
- No audio mutation.
- No recommendation algorithm changes.
- No export workflow changes.

## Task 1: Scan progress/cancel domain seam

**Files:**
- Modify: `src/xfinaudio/library/scan_service.py`
- Test: `tests/test_scan_service.py`

**Steps:**
1. Write failing tests for scan progress callback:
   - callback receives total supported file count;
   - callback receives processed count and current path in deterministic order;
   - unsupported files are not counted in total.
2. Write failing test for cancellation:
   - a cancellation token cancels before a later file;
   - scan returns a result indicating cancellation and records scanned so far, or raises typed cancellation error depending chosen design.
3. Run focused tests and confirm RED.
4. Implement small models/classes:
   - `ScanProgress(processed_count, total_count, current_path)`;
   - `ScanCancellationToken` with `cancel()` and `is_cancelled`;
   - `ScanCancelledError` or `ScanResult(cancelled=True)`.
5. Preserve existing `scan_folder(...) -> list[TrackRecord]` API for compatibility by making progress/cancel optional and returning list when not canceled.
6. Consider adding `scan_folder_with_progress(...)` if easier to avoid breaking existing callers.
7. Run focused tests and full suite.

## Task 2: Workflow service cancel safety

**Files:**
- Modify: `src/xfinaudio/application/playlist_workflow.py`
- Test: `tests/test_playlist_workflow.py`

**Steps:**
1. Write failing test that canceled scan does not call repository `save_scan_results`.
2. Run focused test and confirm RED.
3. Update workflow service to accept optional progress callback/cancellation token.
4. If scan is canceled, return a result with `cancelled=True`, zero persisted state, and partial records only if useful for display.
5. Preserve existing scan success behavior.
6. Run focused tests and full suite.

## Task 3: Desktop scan progress/cancel UI state

**Files:**
- Modify: `src/xfinaudio/desktop/main_window.py`
- Test: `tests/test_main_window.py`

**Steps:**
1. Write failing tests:
   - window has a Cancel Scan button initially disabled;
   - starting a scan enables cancel/status progress state;
   - after successful scan cancel button disables;
   - calling cancel updates status and token;
   - canceled scan status says canceled and does not persist partial results via workflow behavior.
2. Run focused tests and confirm RED.
3. Add `cancel_scan_button`, `scan_progress_label`, and current cancellation token state.
4. Wire progress callback to update progress label.
5. Wire cancel button to token cancel and status text.
6. Keep synchronous scan for now; do not claim real-time cancellation during a blocking mutagen call.
7. Run focused tests and full suite.

## Task 4: Documentation/backlog/evidence

**Files:**
- Create: `docs/scan-progress-cancel.md`
- Modify: `docs/open-source-release-backlog.md`
- Modify: `docs/release-candidate-evidence.md`

**Steps:**
1. Document current cooperative/synchronous limitation and future background-worker path.
2. Mark Desktop UX P1 scan progress feedback completed/partially completed with caveat if no thread.
3. Add verification evidence.
4. Run:
   - `uv run pytest -v tests/test_scan_service.py tests/test_playlist_workflow.py tests/test_main_window.py`
   - `uv run pytest -v`
   - `uv run ruff check .`
   - `uv run ruff format --check .`
5. Fresh review before claiming done.
