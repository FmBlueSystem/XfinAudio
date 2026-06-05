# PyInstaller Pinned Launch Validation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Pin PyInstaller into the project workflow and validate a temp-built XfinAudio app can launch in controlled smoke mode without touching user app data.

**Architecture:** Add a packaging smoke mode to the desktop entrypoint via environment variables. Extend the PyInstaller smoke script to build into temp directories and optionally run the built app/executable with temp DB/settings paths. No release artifacts are committed.

**Tech Stack:** Python 3.11+, PySide6, PyInstaller, uv, pytest, ruff.

---

## Non-goals

- No committed `dist/` or `build/` artifacts.
- No installer DMG/pkg creation.
- No signing/notarization automation.
- No release publishing.
- No product behavior changes outside explicit smoke env vars.
- No live Serato writes or audio mutation.

## Task 1: Pin PyInstaller in project dev dependencies

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Test: `tests/test_pyinstaller_packaging.py`

**Steps:**
1. Write failing test asserting `pyinstaller` is present in the dev dependency group.
2. Run focused test and confirm RED.
3. Add exact `pyinstaller==6.20.0` to `[dependency-groups].dev` using `uv add --dev pyinstaller==6.20.0` or equivalent.
4. Verify `uv run pyinstaller --version` still works from project env.
5. Run focused test.

## Task 2: Desktop package smoke mode

**Files:**
- Modify: `src/xfinaudio/desktop/app.py`
- Test: `tests/test_pyinstaller_packaging.py` or `tests/test_app_entrypoint.py`

**Steps:**
1. Write failing tests for app smoke mode helpers:
   - `XFINAUDIO_PACKAGE_SMOKE=1` causes `main()` to initialize and exit `0` without entering event loop;
   - `XFINAUDIO_DB_PATH` overrides default DB path;
   - `XFINAUDIO_SETTINGS_PATH` overrides default settings path.
2. Run focused test and confirm RED.
3. Implement small helpers:
   - `package_smoke_enabled()`;
   - `database_path_from_environment()`;
   - `settings_path_from_environment()`.
4. In `main()`, construct `QApplication` and `MainWindow.with_defaults(db_path, settings_path)`; if smoke enabled, return `0` before `show()`/`exec()`.
5. Ensure tests use temporary DB/settings paths so no `~/.xfinaudio` writes occur.
6. Run focused tests and full suite.

## Task 3: Build-temp launch validation

**Files:**
- Modify: `scripts/pyinstaller_build_smoke.py`
- Test: `tests/test_pyinstaller_packaging.py`

**Steps:**
1. Write failing tests for new CLI option `--validate-launch`:
   - cannot be used without `--build-temp`;
   - script contains environment variables `XFINAUDIO_PACKAGE_SMOKE`, `XFINAUDIO_DB_PATH`, and `XFINAUDIO_SETTINGS_PATH`;
   - launch validation uses temp DB/settings paths.
2. Run focused test and confirm RED.
3. Implement `--validate-launch` with `--build-temp`:
   - after build, locate macOS app executable under temp dist (`XfinAudio.app/Contents/MacOS/XfinAudio`) or fallback onedir executable;
   - run executable with smoke env vars and a timeout;
   - report stdout/stderr and return non-zero on failure.
4. Run check-only and focused tests.
5. Run `uv run python scripts/pyinstaller_build_smoke.py --build-temp --validate-launch` if feasible and record result.

## Task 4: Documentation/evidence updates

**Files:**
- Modify: `docs/pyinstaller-packaging-spike.md`
- Modify: `docs/packaging-strategy.md`
- Modify: `docs/release-candidate-evidence.md`
- Modify: `docs/open-source-release-backlog.md`

**Steps:**
1. Document pinned PyInstaller dependency and smoke launch env vars.
2. Document temp launch validation result and limitations.
3. Preserve caveats: no installer, no signing/notarization, no release artifact, manual desktop QA still pending.
4. Run:
   - `uv run python scripts/pyinstaller_build_smoke.py --check-only`
   - `uv run pytest -v tests/test_pyinstaller_packaging.py`
   - `uv run pytest -q`
   - `uv run ruff check .`
   - `uv run ruff format --check .`
5. Fresh review before claiming done.
