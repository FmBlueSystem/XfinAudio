# Apply Progress: Scan entry shell methods explicit

Status: complete

## RED

Command:

```bash
uv run pytest tests/test_main_window_shell_compat.py::test_scan_entry_shell_methods_are_explicit_main_window_methods -q
```

Result: failed as expected because `scan_selected_folder` was still present in `shell_layout_compat.LEGACY_LAYOUT_METHODS`.

## GREEN

Changes:
- Added explicit `MainWindow.scan_selected_folder()` delegating to `ScanService.scan_selected_folder()`.
- Added explicit `MainWindow._begin_scan_state()` delegating to `ScanService.begin_scan_state()`.
- Added explicit `MainWindow.cancel_scan()` delegating to `ScanService.cancel()`.
- Added explicit `MainWindow._clear_scan_dependent_state()` delegating to `LibraryController.clear_scan_dependent_state()`.
- Removed the four Scan entry names from `shell_layout_compat.LEGACY_LAYOUT_METHODS`.
- Updated architecture docs and elimination plan progress.

Focused command:

```bash
uv run pytest tests/test_main_window_shell_compat.py::test_scan_entry_shell_methods_are_explicit_main_window_methods -q
```

Result: `1 passed`.


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

Result: all verification gates passed. The legacy layout graft map now has 28 methods, and the four Scan entry names are absent.
