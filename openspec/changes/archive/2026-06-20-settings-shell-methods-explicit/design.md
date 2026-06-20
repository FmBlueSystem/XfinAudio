# Design: Settings shell methods explicit

## Current State
`_open_settings_dialog` and `_on_spectral_cohesion_changed` are dynamically grafted onto `MainWindow` from `desktop/layout.py` through `shell_layout_compat.LEGACY_LAYOUT_METHODS`.

## Approach
Add two thin explicit methods to `MainWindow` that delegate to `self._settings_controller`. Remove the two method names from `shell_layout_compat.LEGACY_LAYOUT_METHODS`.

## Affected Files
- `src/xfinaudio/desktop/main_window.py` — explicit delegators.
- `src/xfinaudio/desktop/shell_layout_compat.py` — remove settings names from graft map.
- `tests/test_main_window_shell_compat.py` — regression coverage.
- `docs/architecture/layered-architecture.md` — slice status.
- `docs/architecture/shell-layout-compat-elimination-plan.md` — progress tracker.
- `openspec/changes/settings-shell-methods-explicit/` — SDD artifacts.

## Safety
No settings behavior, audio behavior, export behavior, DSP, dependencies, or live Serato DB V2 interactions change.
