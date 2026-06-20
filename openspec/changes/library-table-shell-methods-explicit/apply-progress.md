# Apply Progress: Library table shell methods explicit

Status: complete

## RED

Command:

```bash
uv run pytest tests/test_main_window_shell_compat.py::test_library_table_shell_methods_are_explicit_main_window_methods -q
```

Result: failed as expected because `_on_library_selection_changed` was still present in `shell_layout_compat.LEGACY_LAYOUT_METHODS`.

## GREEN

Changes:
- Added explicit `MainWindow._on_library_selection_changed()` delegating to `LibraryController.on_library_selection_changed()`.
- Added explicit `MainWindow.show_tracks()` delegating to `LibraryController.show_tracks()` while preserving optional count defaults.
- Added explicit `MainWindow.set_selected_folder()` delegating to `LibraryController.set_selected_folder()`.
- Added explicit `MainWindow._persist_last_scan_folder()` delegating to `LibraryController._persist_last_scan_folder()`.
- Added explicit `MainWindow._populate_track_table()` delegating to `LibraryController.populate_track_table()`.
- Added explicit `MainWindow._apply_song_filter()` delegating to `LibraryController.apply_song_filter()`.
- Added explicit `MainWindow.restore_persisted_tracks()` delegating to `LibraryController.restore_persisted_tracks()`.
- Removed the seven Library table names from `shell_layout_compat.LEGACY_LAYOUT_METHODS`.
- Updated architecture docs and elimination plan progress.

Focused commands:

```bash
uv run pytest tests/test_main_window_shell_compat.py -q
uv run pytest tests/test_main_window.py::test_main_window_persists_selected_scan_folder_for_future_refresh tests/test_main_window.py::test_populate_track_table_updates_path_mapping_before_reapplying_filter tests/test_main_window.py::test_main_window_filters_library_by_song_title tests/test_main_window.py::test_main_window_filter_uses_path_index_instead_of_rescanning_records tests/test_main_window.py::test_main_window_saved_library_status_uses_readable_summary_not_clipped_sentence tests/test_main_window_player.py::TestSelectionChangeStopsPlayer::test_new_selection_stops_current_preview -q
```

Result: `15 passed`; `6 passed`.

The legacy layout graft map now has 21 methods, and the seven Library table names are absent.


## VERIFY

Commands:

```bash
uv run pytest -q
uv run pyright src tests
uv run pytest --cov --cov-fail-under=70 -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/release_gate_check.py --run
```

Result: all verification gates passed. The legacy layout graft map now has 21 methods, and the seven Library table names are absent.
