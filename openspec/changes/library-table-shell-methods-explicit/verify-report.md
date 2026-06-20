# Verify Report: Library table shell methods explicit

Status: passed

## Requirement: Library table methods are explicit MainWindow methods

Evidence:

```bash
uv run pytest tests/test_main_window_shell_compat.py::test_library_table_shell_methods_are_explicit_main_window_methods -q
```

Result: `1 passed` after the seven Library table names were removed from `LEGACY_LAYOUT_METHODS` and defined directly on `MainWindow`.

## Requirement: Library table behavior remains delegated

Evidence:

```bash
uv run pytest tests/test_main_window_shell_compat.py -q
uv run pytest tests/test_main_window.py::test_main_window_persists_selected_scan_folder_for_future_refresh tests/test_main_window.py::test_populate_track_table_updates_path_mapping_before_reapplying_filter tests/test_main_window.py::test_main_window_filters_library_by_song_title tests/test_main_window.py::test_main_window_filter_uses_path_index_instead_of_rescanning_records tests/test_main_window.py::test_main_window_saved_library_status_uses_readable_summary_not_clipped_sentence tests/test_main_window_player.py::TestSelectionChangeStopsPlayer::test_new_selection_stops_current_preview -q
```

Result: `15 passed`; `6 passed`.

## Requirement: Unrelated grafts stay stable

Evidence:

```bash
uv run pytest -q
uv run pyright src tests
uv run pytest --cov --cov-fail-under=70 -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/release_gate_check.py --run
```

Result:
- `930 passed, 40 warnings`
- `0 errors, 0 warnings, 0 informations`
- `930 passed`, coverage `90.10%`
- `All checks passed!`
- `219 files already formatted`
- Release gate passed, including release readiness smoke, publication docs, artifact hygiene, source package hygiene, and PyInstaller check-only.

## Legacy graft map evidence

Result:
- `remaining_legacy_layout_methods 21`
- `removed library table present? False`
