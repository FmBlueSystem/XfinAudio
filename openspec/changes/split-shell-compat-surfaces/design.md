# Design: Split Shell Compatibility Surfaces

## Approach
Create two focused modules under `xfinaudio.desktop`:

- `shell_layout_compat.py` owns `LEGACY_LAYOUT_METHODS` and `install_legacy_layout_methods()`.
- `shell_state_compat.py` owns AppState-backed read/write compatibility, delegated read aliases, and missing-attribute sentinel handling.

Keep `shell_compat.py` as a thin facade that re-exports the existing public names, preserving current imports while making responsibility boundaries explicit.

## Affected Files
- `src/xfinaudio/desktop/shell_layout_compat.py` — new layout compatibility surface.
- `src/xfinaudio/desktop/shell_state_compat.py` — new state compatibility surface.
- `src/xfinaudio/desktop/shell_compat.py` — thin facade only.
- `tests/test_main_window_shell_compat.py` — RED/GREEN coverage for separate modules and facade stability.
- `openspec/changes/split-shell-compat-surfaces/*` — SDD artifacts.

## Safety
The implementation moves existing functions without changing their logic. `MainWindow` can keep importing `shell_compat` during this slice to avoid widening the change.

## Review Budget
Expected diff is under 400 changed lines.
