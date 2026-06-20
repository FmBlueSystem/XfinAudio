# Design: Copilot variant shell bridge explicit

## Approach

Add a thin `MainWindow._on_copilot_variant_applied(index: int)` method beside the existing Prep Copilot explicit methods. The method delegates to `self._prep_copilot.on_variant_applied(index)`.

Remove only the `_on_copilot_variant_applied` entry from `shell_layout_compat.LEGACY_LAYOUT_METHODS`. Keep spectral completion grafts unchanged for the next slice.

## Affected files

- `src/xfinaudio/desktop/main_window.py`
- `src/xfinaudio/desktop/shell_layout_compat.py`
- `tests/test_main_window_shell_compat.py`
- `docs/architecture/layered-architecture.md`
- `docs/architecture/shell-layout-compat-elimination-plan.md`
