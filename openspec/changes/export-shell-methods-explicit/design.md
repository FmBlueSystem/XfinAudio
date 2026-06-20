# Design: Export shell methods explicit

## Current State
`shell_layout_compat.LEGACY_LAYOUT_METHODS` dynamically grafts layout-backed methods onto `MainWindow`. The Export / Safe Export group already has a clearer behavior owner in `ExportActions`, backed by `ExportCoordinator` for export operations.

## Approach
Add thin explicit methods to `MainWindow` for the selected Export / Safe Export names. Each method delegates to `self._export_actions` or the existing settings controller formatter. Remove the selected names from `shell_layout_compat.LEGACY_LAYOUT_METHODS`.

## Affected Files
- `src/xfinaudio/desktop/main_window.py` — add explicit delegators.
- `src/xfinaudio/desktop/shell_layout_compat.py` — remove selected export names from the graft map.
- `tests/test_main_window_shell_compat.py` — add regression coverage.
- `docs/architecture/layered-architecture.md` — record slice progress.
- `openspec/changes/export-shell-methods-explicit/` — SDD artifacts.

## Safety
This slice does not change export algorithms or file formats. Export writes remain behind the existing safe export/coordinator flow. No audio mutation, DSP, dependency changes, or live Serato DB V2 writes are introduced.

## Review Budget
Expected to stay under 400 changed lines. If the diff grows beyond the budget, stop and split the slice.
