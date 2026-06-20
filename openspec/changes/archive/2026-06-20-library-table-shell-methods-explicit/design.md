# Design: Library table shell methods explicit

## Approach

Add explicit `MainWindow` delegators for the Library table method group and remove the same names from `shell_layout_compat.LEGACY_LAYOUT_METHODS`.

The slice keeps existing ownership boundaries:
- `MainWindow` exposes compatibility-callable methods.
- Existing Library controller/screen services retain behavior.
- `shell_layout_compat` continues to graft unrelated legacy methods until later slices remove them.

## Affected files

- `src/xfinaudio/desktop/main_window.py`
- `src/xfinaudio/desktop/shell_layout_compat.py`
- `tests/test_main_window_shell_compat.py`
- `docs/architecture/layered-architecture.md`
- `docs/architecture/shell-layout-compat-elimination-plan.md`
- `openspec/changes/library-table-shell-methods-explicit/`

## Safety

No audio files, DSP behavior, dependencies, export formats, or live Serato DB V2 files are changed.
