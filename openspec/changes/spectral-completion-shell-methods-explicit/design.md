# Design: Spectral completion shell methods explicit

## Approach

Add thin `MainWindow` methods for the five spectral completion callbacks. Each method delegates to the existing `LibraryController` method used by the current layout helpers.

Remove all entries from `shell_layout_compat.LEGACY_LAYOUT_METHODS`. Keep the module in place for this slice so callers/imports remain stable; a final safe-removal slice can decide whether to delete the now-empty compatibility surface.

## Affected files

- `src/xfinaudio/desktop/main_window.py`
- `src/xfinaudio/desktop/shell_layout_compat.py`
- `tests/test_main_window_shell_compat.py`
- `docs/architecture/layered-architecture.md`
- `docs/architecture/shell-layout-compat-elimination-plan.md`
