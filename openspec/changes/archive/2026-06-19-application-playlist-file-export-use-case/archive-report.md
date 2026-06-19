# Archive Report

Change: `application-playlist-file-export-use-case`
Archived: 2026-06-19

## Summary
Added an Application-layer non-Serato playlist file export use case and updated the desktop export coordinator to call it for Rekordbox, Traktor, and VirtualDJ preview/export paths.

## Verification
- Focused application/export coordinator tests passed.
- `uv run python scripts/release_gate_check.py --run` passed.

## Durable Spec Sync
Updated `openspec/specs/multi-software-export/spec.md` with the Application Export Use Case Boundary requirement.
