# Archive Report

Change: `app-state-library-folder-selection-transition`
Archived: 2026-06-19

## Summary
Extracted library folder selection AppState policy into `apply_library_folder_selected()`, preserving desktop controller responsibilities for settings persistence and UI clearing.

## Verification
- Focused transition/controller tests passed.
- `uv run python scripts/release_gate_check.py --run` passed.

## Durable Spec Sync
Updated `openspec/specs/desktop-main-window/spec.md` with the Library Folder Selection State Boundary requirement.
