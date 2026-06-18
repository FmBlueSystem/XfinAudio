# Design: Slice main_window final

## Approach

Seven mechanical extractions. Each method or dict moves to an existing
controller or factory. The signal wiring in `_connect_screens` and the
per-screen `connect_signals` methods MUST be updated to call the controllers
directly instead of going through the MainWindow shims.

## Files affected

### Modified files (5)

| Path | Change |
|------|--------|
| `src/xfinaudio/desktop/main_window.py` | -330 LOC, +30 LOC of shims and remaining logic |
| `src/xfinaudio/desktop/window_factory.py` | +80 LOC (initialize_library_controller, replace_app_state, initialize_app_controller, with_defaults) |
| `src/xfinaudio/desktop/layout.py` | +50 LOC (install_layout_methods + the 47 methods dict) |
| `src/xfinaudio/desktop/settings_controller.py` | +18 LOC (apply_settings) |
| `src/xfinaudio/desktop/prep_copilot.py` | +10 LOC (set_applied_variant) |
| `src/xfinaudio/desktop/library_controller.py` | +80 LOC (16 _on_* handlers + the 2 _open_selected_* + _remove_selected_*) |

## Method move list

### To `window_factory.py`
- `MainWindow._initialize_library_controller` (33 LOC)
- `MainWindow._replace_app_state` (12 LOC)
- `MainWindow._initialize_app_controller` (32 LOC)
- `MainWindow.with_defaults` (15 LOC)

### To `settings_controller.py`
- `MainWindow._apply_settings` (18 LOC)

### To `prep_copilot.py`
- `MainWindow._set_applied_copilot_variant` (10 LOC)

### To `library_controller.py`
- `MainWindow._on_metadata_export_requested` (6 LOC)
- `MainWindow._on_exclude_requested` (4 LOC)
- `MainWindow._on_lock_requested` (4 LOC)
- `MainWindow._on_clear_constraints` (4 LOC)
- `MainWindow._on_library_filters_cleared` (10 LOC)
- `MainWindow._on_proceed_to_export` (4 LOC)
- `MainWindow._on_track_remove_requested` (12 LOC)
- `MainWindow._apply_track_removed` (3 LOC)
- `MainWindow._apply_track_restored` (3 LOC)
- `MainWindow._on_track_play_requested` (6 LOC)
- `MainWindow._on_preview_play_requested` (3 LOC)
- `MainWindow._on_live_load_next` (2 LOC)
- `MainWindow._on_player_state_changed` (7 LOC)
- `MainWindow._on_player_error` (4 LOC)
- `MainWindow._open_selected_library_track` (7 LOC)
- `MainWindow._remove_selected_review_track` (5 LOC)

### To `layout.py`
- The `_LAYOUT_METHODS` dict and the `setattr` loop (50 LOC)

### Removed (replaced by direct controller calls)
- `MainWindow.undo` (1 LOC)
- `MainWindow.redo` (1 LOC)
- `MainWindow._refresh_undo_state` (1 LOC)
- `MainWindow._build_undo_toolbar` (6 LOC)
- `MainWindow._connect_keyboard_shortcuts` (2 LOC)
- `MainWindow._set_status_bar_visible` (3 LOC)
- `MainWindow.show_status_bar` (2 LOC)
- `MainWindow._apply_compact_table_columns` (2 LOC)
- `MainWindow._apply_visual_design` (2 LOC)
- `MainWindow._connect_table_sorting` (6 LOC)
- `MainWindow._sort_table_by_column` (6 LOC)
- `MainWindow._apply_compact_mac_layout` (2 LOC)
- `MainWindow._set_recommendation_sections_expanded` (10 LOC)
- `MainWindow._open_settings_dialog` (5 LOC)
- `MainWindow._on_spectral_cohesion_changed` (8 LOC)
- `MainWindow.set_safe_export_folder` (2 LOC)
- `MainWindow.choose_safe_export_folder` (2 LOC)
- `MainWindow._format_safe_export_folder_label` (4 LOC)

## Step-by-step

1. Pre-flight: 848 tests pass.
2. Move the 4 factory methods to `window_factory.py`. Update `__init__` to call
   the factory functions. Run pytest. Green.
3. Move `_apply_settings` to `settings_controller.py`. Update the call site.
   Run pytest. Green.
4. Move `_set_applied_copilot_variant` to `prep_copilot.py`. Update the call
   site. Run pytest. Green.
5. Move the 16 `_on_*` handlers to `library_controller.py`. Update the call
   sites (the signal connections in `_connect_screens` and per-screen
   `connect_signals`). Run pytest. Green.
6. Move the `_LAYOUT_METHODS` dict and `setattr` loop to `layout.py` as
   `install_layout_methods(target_class)`. Call it from main_window's class
   definition. Run pytest. Green.
7. Remove the 1-line shim methods. Update the call sites. Run pytest. Green.
8. Run full verify: pytest, ruff, pyright, hygiene check.
9. `wc -l src/xfinaudio/desktop/main_window.py` is under 400.

## Risks

- **Removing shims requires updating many call sites**: each shim is used by
  signal connections, the menu, the per-screen `connect_signals`, and the
  services. The apply step MUST grep for every removed shim and update its
  callers.
- **`install_layout_methods` timing**: the dict-based setattr must happen at
  class definition time (after the class body, before any usage). The apply
  step MUST verify that `MainWindow.choose_folder` is callable after
  `install_layout_methods(MainWindow)` is called.
- **Library controller parameter explosion**: the LibraryController currently
  has 8 parameters. Adding 16 methods and 1 dependency (`_audio_player` is
  already there) keeps it manageable but it grows. If the constructor exceeds
  15 parameters, the apply step MUST report.

## Rollback

Single `git revert <commit-sha>` restores the previous state.
