# Apply Progress: Metadata filter shell methods explicit

Status: complete

## RED

Command:

```bash
uv run pytest tests/test_main_window_shell_compat.py::test_metadata_filter_shell_methods_are_explicit_main_window_methods -q
```

Result: failed as expected because `_selected_metadata_status_filter` was still present in `shell_layout_compat.LEGACY_LAYOUT_METHODS`.

## GREEN

Changes:
- Added explicit `MainWindow._selected_metadata_status_filter()` delegating to `LibraryController.selected_metadata_status_filter()`.
- Added explicit `MainWindow._selected_missing_metadata_filter()` delegating to `LibraryController.selected_missing_metadata_filter()`.
- Added explicit `MainWindow._metadata_status_records()` delegating to `LibraryController.metadata_status_records()`.
- Added explicit `MainWindow._metadata_missing_field_records()` delegating to `LibraryController.metadata_missing_field_records()`.
- Removed the four Metadata filter names from `shell_layout_compat.LEGACY_LAYOUT_METHODS`.
- Updated architecture docs and elimination plan progress.

Focused commands:

```bash
uv run pytest tests/test_main_window_shell_compat.py::test_metadata_filter_shell_methods_are_explicit_main_window_methods -q
uv run pytest tests/test_main_window_shell_compat.py tests/test_library_filter.py -q
```

Result: `1 passed`; `24 passed`.

The legacy layout graft map now has 17 methods, and the four Metadata filter names are absent.


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

Result: all verification gates passed. The legacy layout graft map now has 17 methods, and the four Metadata filter names are absent.
