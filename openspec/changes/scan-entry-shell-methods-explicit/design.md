# Design: Scan entry shell methods explicit

## Current State
The selected scan entry methods are dynamically grafted onto `MainWindow` from `desktop/layout.py` through `shell_layout_compat.LEGACY_LAYOUT_METHODS`.

## Approach
Add thin explicit methods to `MainWindow`:
- `scan_selected_folder()` delegates to `self._scan_service.scan_selected_folder()`.
- `_begin_scan_state()` delegates to `self._scan_service.begin_scan_state()`.
- `cancel_scan()` delegates to `self._scan_service.cancel()`.
- `_clear_scan_dependent_state()` delegates to `self._library_controller.clear_scan_dependent_state()`.

Remove the four names from `shell_layout_compat.LEGACY_LAYOUT_METHODS`.

## Affected Files
- `src/xfinaudio/desktop/main_window.py` — explicit delegators.
- `src/xfinaudio/desktop/shell_layout_compat.py` — remove scan entry names from graft map.
- `tests/test_main_window_shell_compat.py` — regression coverage.
- `docs/architecture/layered-architecture.md` — slice status.
- `docs/architecture/shell-layout-compat-elimination-plan.md` — progress tracker.
- `openspec/changes/scan-entry-shell-methods-explicit/` — SDD artifacts.

## Safety
No scan behavior, worker lifecycle, cancellation semantics, audio behavior, DSP, dependencies, or live Serato DB V2 interactions change.
