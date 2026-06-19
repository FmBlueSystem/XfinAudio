# Design: Desktop shell compatibility boundary

## Approach

Create `src/xfinaudio/desktop/shell_compat.py` as the explicit home for legacy MainWindow method grafting. Move the `_LAYOUT_METHODS` mapping and installer out of `layout.py`, leaving layout focused on building widgets/layout helpers.

`main_window.py` will import `shell_compat` and call `shell_compat.install_legacy_layout_methods(MainWindow)` at module load, preserving current behavior while naming the debt.

## Files

- `src/xfinaudio/desktop/shell_compat.py` — new compatibility boundary and legacy method mapping.
- `src/xfinaudio/desktop/layout.py` — remove compatibility installer responsibility.
- `src/xfinaudio/desktop/main_window.py` — call the explicit compatibility installer.
- `tests/test_main_window_shell_compat.py` — focused tests for boundary ownership and method availability.
- `docs/architecture/layered-architecture.md` — mark Slice 5 as started/in progress only if implementation proceeds in this PR.

## Safety

No product behavior changes. No audio mutation. No DSP scope. No storage or export behavior changes. No live Serato DB V2 writes.

## Review budget

Expected under 400 changed lines. If the mapping move grows beyond that, stop and split.
