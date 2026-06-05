# Packaging Strategy and Release Notes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Define XfinAudio's release packaging strategy and release notes template so future distribution work has clear decisions, constraints, and verification gates.

**Architecture:** Documentation-only slice. Use review-friendly docs that lead with decisions and checklists. Do not add packaging tooling, installer builds, signing automation, or distribution scripts yet.

**Tech Stack:** Python 3.11+, PySide6, uv, hatchling, pytest, ruff, future PyInstaller candidate for desktop packaging.

---

## Non-goals

- No installer/build artifact creation.
- No code changes.
- No signing/notarization automation.
- No release publishing.
- No live Serato writes or audio mutation.

## Task 1: Packaging strategy document

**Files:**
- Create: `docs/packaging-strategy.md`

**Steps:**
1. Document the recommended RC packaging path:
   - near-term developer/QA run: `uv run xfinaudio`;
   - first distributable candidate: PyInstaller app bundle;
   - keep hatchling wheel for library/package structure validation, not end-user desktop distribution.
2. Include target platforms:
   - macOS first, because current development path is macOS;
   - Windows/Linux as future validation targets.
3. Include signing/notarization notes:
   - macOS Developer ID signing and notarization required before binary/app bundle redistribution;
   - unsigned builds are internal QA only.
4. Include app-owned paths:
   - DB: `~/.xfinaudio/xfinaudio.sqlite3`;
   - settings: `~/.xfinaudio/settings.json`.
5. Include release build gates:
   - full pytest;
   - ruff check/format;
   - release smoke script;
   - manual desktop QA with real Mixed In Key folder;
   - no live Serato writes.
6. Include open decisions and risks.

## Task 2: Release notes template

**Files:**
- Create: `docs/release-notes-template.md`

**Steps:**
1. Create a reusable template with sections:
   - version/date;
   - summary;
   - who should use it;
   - what is included;
   - what is explicitly out of scope;
   - verification evidence;
   - known limitations;
   - safe-use warnings;
   - upgrade/data notes;
   - support/troubleshooting.
2. Include explicit safety warnings:
   - no audio mutation;
   - no live Serato writes;
   - Serato fixture validation is not live compatibility;
   - manual desktop QA requirement.
3. Keep template concise and copy-pasteable.

## Task 3: Backlog and evidence updates

**Files:**
- Modify: `docs/open-source-release-backlog.md`
- Modify: `docs/release-candidate-evidence.md`

**Steps:**
1. Mark Packaging strategy P1 completed with evidence link.
2. Mark Release notes template P1 completed with evidence link.
3. Add docs verification evidence and note that no build artifact was produced.

## Task 4: Verification and review

**Steps:**
1. Run:
   - `uv run pytest -q`
   - `uv run ruff check .`
   - `uv run ruff format --check .`
2. Fresh review docs for clarity, safety constraints, and no false release claims.
