# Design: MainWindow explicit shell compatibility surfaces

## Approach
Replace the single `MainWindow` import of `desktop.shell_compat` with two explicit module imports:
- `desktop.shell_layout_compat` for `install_legacy_layout_methods`.
- `desktop.shell_state_compat` for AppState-backed read/write compatibility helpers.

`desktop.shell_compat` remains a facade that re-exports the same public names for legacy/external import compatibility.

## Affected files
- `src/xfinaudio/desktop/main_window.py` — migrate import and call sites to explicit modules.
- `tests/test_main_window_shell_compat.py` — add source-level guard for direct facade coupling.
- `openspec/changes/mainwindow-explicit-shell-surfaces/` — SDD artifacts and evidence.

## Safety
This is a wiring-only refactor. It does not change AppState semantics, layout grafting behavior, audio files, DSP behavior, Serato export behavior, or dependencies.
