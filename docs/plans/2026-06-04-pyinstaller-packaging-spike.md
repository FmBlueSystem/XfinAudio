# PyInstaller Packaging Spike Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a safe PyInstaller packaging spike for XfinAudio that validates packaging configuration without committing heavy build artifacts.

**Architecture:** Keep the repo artifact to a PyInstaller spec/config, smoke script, docs, and tests. Any actual PyInstaller build must run only into temporary directories and must not leave `dist/` or `build/` artifacts in the project root.

**Tech Stack:** Python 3.11+, PySide6, PyInstaller, uv, pytest, ruff.

---

## Non-goals

- No committed `dist/` or `build/` artifacts.
- No installer DMG/pkg creation.
- No code signing or notarization automation.
- No publishing/release upload.
- No product behavior changes.
- No live Serato writes or audio mutation.

## Task 1: Build artifact hygiene

**Files:**
- Modify: `.gitignore`
- Test: `tests/test_pyinstaller_packaging.py`

**Steps:**
1. Write failing test asserting repo `.gitignore` ignores PyInstaller artifact directories/files:
   - `build/`
   - `dist/`
   - `*.spec` should **not** be globally ignored because the project spec is committed under `packaging/pyinstaller/`.
2. Run focused test and confirm RED.
3. Update `.gitignore` with `build/` and `dist/` if missing.
4. Run focused test.

## Task 2: PyInstaller spec

**Files:**
- Create: `packaging/pyinstaller/xfinaudio.spec`
- Test: `tests/test_pyinstaller_packaging.py`

**Steps:**
1. Write failing tests asserting:
   - spec exists at `packaging/pyinstaller/xfinaudio.spec`;
   - spec references `src/xfinaudio/desktop/app.py` as entry;
   - spec sets app name `XfinAudio`;
   - spec includes `src` in `pathex` or equivalent;
   - spec does not reference audio folders, Serato live paths, or user home paths.
2. Run focused test and confirm RED.
3. Create a minimal PyInstaller spec for onedir/app-bundle candidate:
   - entry `src/xfinaudio/desktop/app.py`;
   - name `XfinAudio`;
   - no icon yet;
   - no data files yet;
   - avoid hardcoded user paths.
4. Run focused test.

## Task 3: Temporary build smoke script

**Files:**
- Create: `scripts/pyinstaller_build_smoke.py`
- Test: `tests/test_pyinstaller_packaging.py`

**Steps:**
1. Write failing tests for script behavior:
   - `--check-only` prints PyInstaller version and spec path;
   - check-only does not create project `dist/` or `build/`;
   - script command docs mention temp `--distpath` and `--workpath`.
2. Run focused test and confirm RED.
3. Implement script:
   - default mode is check-only;
   - optional `--build-temp` creates temporary build/work/dist dirs and runs PyInstaller there;
   - always prints artifact paths;
   - exits non-zero on PyInstaller failure;
   - never writes `dist/` or `build/` under repo root.
4. Run check-only focused test.
5. If feasible, run `uv run python scripts/pyinstaller_build_smoke.py --build-temp` once. If it fails, record blocker details; do not hide failure.

## Task 4: Documentation/backlog/evidence

**Files:**
- Create: `docs/pyinstaller-packaging-spike.md`
- Modify: `docs/packaging-strategy.md`
- Modify: `docs/release-candidate-evidence.md`
- Modify: `docs/open-source-release-backlog.md`

**Steps:**
1. Document:
   - what config was added;
   - how to run check-only;
   - how to run temp build smoke;
   - where artifacts go;
   - what remains before real binary/app bundle redistribution.
2. Update packaging strategy with spike status.
3. Update evidence with verification/build-smoke result.
4. Do not claim installer/signing/notarization/release exists.

## Task 5: Verification and fresh review

**Steps:**
1. Run:
   - `uv run python scripts/pyinstaller_build_smoke.py --check-only`
   - `uv run pytest -v tests/test_pyinstaller_packaging.py`
   - `uv run pytest -q`
   - `uv run ruff check .`
   - `uv run ruff format --check .`
2. Run `uv run python scripts/pyinstaller_build_smoke.py --build-temp` if time/resources permit and record result.
3. Fresh review before claiming done.
