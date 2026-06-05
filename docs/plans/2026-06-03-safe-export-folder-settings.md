# Safe Export Folder Settings Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Persist a user-selected safe export folder so XfinAudio never defaults exports into audio library folders.

**Architecture:** Add versioned JSON settings persistence using existing pydantic settings models. Keep this as settings/UI readiness only; do not implement playlist export buttons or live Serato writes. The UI can choose and display the safe folder, while export code remains caller-managed.

**Tech Stack:** Python 3.11+, pydantic, PySide6, pytest, ruff, uv, standard-library json/pathlib.

---

## Non-goals

- No desktop playlist export workflow implementation.
- No live Serato writes.
- No audio file mutation.
- No change to recommendation algorithms.
- No platform-specific settings backend; use app-owned JSON for MVP.

## Task 1: Export settings model

**Files:**
- Modify: `src/xfinaudio/config/settings.py`
- Test: `tests/test_settings.py`

**Steps:**
1. Write failing tests for `AppSettings().export.safe_export_folder is None`.
2. Write failing tests that a path can be stored as `safe_export_folder`.
3. Write failing tests rejecting audio-library-default behavior if needed: the model should not infer export folder from scan folder.
4. Run focused tests and confirm RED.
5. Add `ExportSettings` with `safe_export_folder: Path | None = None`.
6. Add `export: ExportSettings` to `AppSettings`.
7. Run focused tests and full suite.

## Task 2: JSON settings repository

**Files:**
- Create: `src/xfinaudio/config/settings_repository.py`
- Test: `tests/test_settings_repository.py`

**Steps:**
1. Write failing tests:
   - missing file returns default `AppSettings`;
   - saving then loading preserves safe export folder;
   - future settings version raises validation error and does not silently downgrade;
   - malformed JSON raises a typed settings error.
2. Run focused tests and confirm RED.
3. Implement `SettingsRepository` with `load()` and `save(settings)`.
4. Implement `SettingsRepositoryError` for malformed JSON / invalid file shape; allow pydantic validation errors to be wrapped or raised consistently.
5. Save JSON with sorted keys and indentation for supportability.
6. Ensure it writes only caller-provided app settings path.
7. Run focused tests and full suite.

## Task 3: Desktop safe export folder selector/display

**Files:**
- Modify: `src/xfinaudio/desktop/app.py`
- Modify: `src/xfinaudio/desktop/main_window.py`
- Test: `tests/test_main_window.py`

**Steps:**
1. Write failing tests for `MainWindow` constructed with settings repository/settings:
   - initial safe export label says no safe export folder selected;
   - existing safe export folder is displayed;
   - selecting a safe export folder updates settings, persists them, and updates label;
   - selected export folder must not equal selected audio scan folder.
2. Run focused tests and confirm RED.
3. Add a small protocol/type for settings persistence if needed.
4. Add UI button `Choose Safe Export Folder` and label.
5. Add method `set_safe_export_folder(folder: Path)` for tests and picker callback for runtime.
6. Validation: if selected export folder equals `selected_folder`, set status warning and do not persist.
7. Wire `MainWindow.with_defaults()` to use default settings path.
8. Keep export workflow out of scope; label should say this folder will be used by future safe export actions.
9. Run focused tests and full suite.

## Task 4: Documentation/backlog/evidence

**Files:**
- Create: `docs/safe-export-folder-settings.md`
- Modify: `docs/open-source-release-backlog.md`
- Modify: `docs/release-candidate-evidence.md`

**Steps:**
1. Document app settings path, JSON schema behavior, and safe export folder policy.
2. Mark P1 `Remember safe export folder` completed with caveat: export UI is still future work.
3. Add verification evidence.
4. Run:
   - `uv run pytest -v tests/test_settings.py tests/test_settings_repository.py tests/test_main_window.py`
   - `uv run pytest -v`
   - `uv run ruff check .`
   - `uv run ruff format --check .`
5. Fresh review before claiming done.
