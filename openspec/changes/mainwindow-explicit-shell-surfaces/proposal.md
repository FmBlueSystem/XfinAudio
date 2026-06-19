# Proposal: MainWindow explicit shell compatibility surfaces

## Intent
Move internal `MainWindow` shell compatibility wiring away from the legacy `desktop.shell_compat` facade and onto the narrower compatibility surfaces introduced by the previous slice.

## Problem
`desktop.shell_compat` is already a thin compatibility facade, but `MainWindow` still imports it directly for both layout grafting and AppState compatibility. That keeps an internal production caller coupled to the umbrella legacy surface and weakens the boundary created by the split.

## Scope
In scope:
- Add focused RED coverage proving `MainWindow` does not import `desktop.shell_compat` directly.
- Update `MainWindow` to use `shell_layout_compat` and `shell_state_compat` directly.
- Preserve `shell_compat.py` as an import-compatible facade for external/legacy callers.
- Keep visible desktop behavior unchanged.

Out of scope:
- Removing `shell_compat.py`.
- Changing layout behavior, AppState compatibility semantics, or screen wiring.
- Audio mutation, DSP, Serato DB V2 writes, or dependency changes.

## Success criteria
- Focused shell compatibility tests pass.
- `MainWindow` has no direct import/reference to `shell_compat`.
- The compatibility facade remains import-compatible.
- Full project verification passes.
- Review size remains below the 400-line budget.

## Rollback
Revert the `MainWindow` import and call sites to use `desktop.shell_compat` while keeping the narrower modules intact.
