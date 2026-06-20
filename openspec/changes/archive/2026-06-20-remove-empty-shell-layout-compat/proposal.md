# Proposal: Remove empty shell layout compatibility surface

## Intent

Remove the empty `shell_layout_compat` dynamic graft surface after all layout methods became explicit `MainWindow` methods.

## Scope

In:
- Remove the `MainWindow` import and installation call for `shell_layout_compat`.
- Delete `src/xfinaudio/desktop/shell_layout_compat.py`.
- Remove layout graft reexports from `shell_compat.py`.
- Update shell compatibility tests and architecture docs.

Out:
- No behavior changes to explicit `MainWindow` methods.
- No state compatibility cleanup.
- No audio mutation, DSP, Serato DB writes, or dependency changes.

## Success Criteria

- `main_window.py` no longer references `shell_layout_compat` or `install_legacy_layout_methods`.
- `shell_compat` no longer exposes `LEGACY_LAYOUT_METHODS` or `install_legacy_layout_methods`.
- No `shell_layout_compat.py` source file remains.
- Focused and full release gates pass.
