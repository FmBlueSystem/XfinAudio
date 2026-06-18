## Why

After PR 7, `main_window.py` is 690 LOC — still well over the 400-line review budget.
The remaining bloat is in 7 places, each of which can be moved to an existing
controller or factory.

## What changes

1. **Move `_initialize_library_controller` and `_replace_app_state` and
   `_initialize_app_controller` to `window_factory.py`.** ~80 LOC saved.
2. **Move `with_defaults` classmethod to `window_factory.py`.** ~15 LOC saved.
3. **Move `_apply_settings` to `settings_controller.py`.** ~18 LOC saved.
4. **Move `_set_applied_copilot_variant` to `prep_copilot.py`.** ~10 LOC saved.
5. **Move the small `_on_*` methods (`_on_metadata_export_requested`,
   `_on_exclude_requested`, `_on_lock_requested`, `_on_clear_constraints`,
   `_on_library_filters_cleared`, `_on_proceed_to_export`,
   `_on_track_remove_requested`, `_apply_track_removed`,
   `_apply_track_restored`, `_on_track_play_requested`,
   `_on_preview_play_requested`, `_on_live_load_next`,
   `_on_player_state_changed`, `_on_player_error`,
   `_open_selected_library_track`, `_remove_selected_review_track`)
   to `library_controller.py` (or a new `tracks_controller.py`).** ~80 LOC saved.
6. **Move the `_LAYOUT_METHODS` dict (47 methods via `setattr`) to
   `layout.py`.** ~50 LOC saved.
7. **Remove the 1-line shim methods that forward to controllers
   (`undo`, `redo`, `_refresh_undo_state`, `_build_undo_toolbar`,
   `_connect_keyboard_shortcuts`, `_set_status_bar_visible`,
   `show_status_bar`, `_apply_compact_table_columns`,
   `_apply_visual_design`, `_connect_table_sorting`,
   `_sort_table_by_column`, `_apply_compact_mac_layout`,
   `_set_recommendation_sections_expanded`, `_open_settings_dialog`,
   `_on_spectral_cohesion_changed`, `set_safe_export_folder`,
   `choose_safe_export_folder`, `_format_safe_export_folder_label`).
   Each is now called directly via the controller at the call site.** ~80 LOC saved.

## Non-goals

- Splitting `MainWindow` into a `MainWindowShell` + `App` class. (Out of scope.)
- Renaming any public method on `MainWindow`.
- Changing the test suite's assertion behavior.

## Impact

- Net: ~330 LOC moved out; new main_window: ~360 LOC (under the 400-line budget).
- Several existing controllers extended.
- Review budget: exceeds 400-line cap on purpose (large refactor, same pattern as
  PR 5/6/7).
- Risk: medium. Strict TDD applies: the 848-test suite is the contract.
