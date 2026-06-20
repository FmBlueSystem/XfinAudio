# Design: Library shell methods explicit on MainWindow

## Approach
Add explicit `MainWindow` delegator methods for the smallest Library-owned group:
- `choose_folder()` delegates to `self._library_controller.choose_folder()`.
- `_refresh_idle_action_state()` delegates to `self._library_controller.refresh_idle_action_state()`.

Then remove `choose_folder` and `_refresh_idle_action_state` from `shell_layout_compat.LEGACY_LAYOUT_METHODS`.

## Affected files
- `src/xfinaudio/desktop/main_window.py` — add explicit delegator methods.
- `src/xfinaudio/desktop/shell_layout_compat.py` — remove selected names from graft map.
- `tests/test_main_window_shell_compat.py` — RED/GREEN coverage for explicit ownership.
- `docs/architecture/layered-architecture.md` — record the sub-slice.
- `openspec/changes/library-shell-methods-explicit/` — SDD artifacts.

## Safety
The public method names remain on `MainWindow`, so shortcuts and screen signal wiring continue to call the same target. The implementation delegates to existing `LibraryController` behavior and does not alter product flows.
