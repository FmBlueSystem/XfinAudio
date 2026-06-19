# Design: MainWindow State Compatibility Boundary

## Approach
Extend `xfinaudio.desktop.shell_compat` so it owns legacy AppState write compatibility in addition to legacy layout method installation. `MainWindow.__setattr__` becomes a thin delegator that asks the compatibility boundary whether a write was handled, then falls back to normal assignment.

## Affected Files
- `src/xfinaudio/desktop/shell_compat.py` — add explicit AppState-backed attribute set and write handler.
- `src/xfinaudio/desktop/main_window.py` — delegate `__setattr__` to shell compatibility.
- `tests/test_main_window_shell_compat.py` — add focused RED coverage for the new boundary.
- `openspec/changes/mainwindow-state-compat-boundary/*` — SDD artifacts.

## Safety
The helper will preserve exact existing mappings:
- `_records_by_path` writes to `state.records_by_path`.
- `applied_prep_copilot_variant_name` writes to `state.applied_variant_name`.
- `workflow_service` writes to AppState and mirrors into scan/recommendation services when present.
- `current_scan_cancellation_token` writes to AppState and mirrors into scan service when present.
- Other AppState-backed attributes write through to `_state`.

## Review Budget
Expected diff is under 400 changed lines.
