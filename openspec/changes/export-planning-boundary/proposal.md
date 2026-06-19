# Export Planning Boundary Proposal

## Intent
Separate non-Serato playlist file export planning from the Qt desktop coordinator so path/name/software decisions can be unit-tested without UI fixtures.

## Scope
In scope:
- Add a pure export-planning module under `xfinaudio.exporting` for Rekordbox, Traktor, and VirtualDJ playlist file targets.
- Preserve current target-name precedence: explicit requested name, applied Prep Copilot variant, generated default filename.
- Keep UI copy, translated status messages, writer dispatch, and Serato crate behavior in the desktop/exporting orchestration layers.
- Add focused unit tests for the new pure planning module.

Out of scope:
- Serato crate planning or writing changes.
- Metadata worklist export behavior.
- Audio file mutation, DSP, rendering, mixing, live Serato database V2 writes.

## Risks
- Filename/path behavior must remain identical for existing multi-software exports.
- Unknown software handling must stay deterministic and remain surfaced by desktop UI.

## Rollback
Remove `xfinaudio.exporting.playlist_file_export`, revert `desktop/export_coordinator.py` to inline target path/name planning, and remove the new focused tests.

## Success Criteria
- New planner has unit coverage for requested name, variant name, generated default name, and unknown software rejection.
- `ExportCoordinator.preview_export` and `ExportCoordinator.export_recommendation` consume the pure planner for non-Serato software.
- Focused export tests pass before full verification.
