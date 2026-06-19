# Design: MainWindow Read Compatibility Boundary

## Approach
Extend `xfinaudio.desktop.shell_compat` so it owns legacy read compatibility in addition to layout method grafting and AppState write compatibility. `MainWindow.__getattr__` becomes a thin delegator that asks the compatibility boundary for a read result and raises `AttributeError` only when the boundary reports the attribute is unsupported.

## Affected Files
- `src/xfinaudio/desktop/shell_compat.py` — add read-result sentinel/helper for legacy reads.
- `src/xfinaudio/desktop/main_window.py` — delegate `__getattr__` to shell compatibility.
- `tests/test_main_window_shell_compat.py` — add focused RED coverage for the read boundary.
- `openspec/changes/mainwindow-read-compat-boundary/*` — SDD artifacts.

## Safety
The helper will preserve exact existing read behavior:
- `undo`, `redo`, and `_on_track_remove_requested` delegate to toolbar/controller objects when `_undo_toolbar` exists.
- Unknown private attributes raise `AttributeError`, except `_records_by_path`.
- `_records_by_path` returns `state.records_by_path`.
- `applied_prep_copilot_variant_name` returns `state.applied_variant_name`.
- `current_scan_cancellation_token` syncs from `_scan_service` before returning state.
- Other AppState-backed attributes return from `_state`.

## Review Budget
Expected diff is under 400 changed lines.
