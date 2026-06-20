# Apply Progress: Spectral completion shell methods explicit

Status: verified

## RED

Command:

```bash
uv run pytest tests/test_main_window_shell_compat.py::test_spectral_completion_shell_methods_are_explicit_main_window_methods -q
```

Result: failed as expected because `_start_spectral_completion_worker` was still present in `shell_layout_compat.LEGACY_LAYOUT_METHODS`.

## GREEN

Changes:
- Added explicit `MainWindow` delegators for the five spectral completion lifecycle methods.
- Removed all remaining entries from `LEGACY_LAYOUT_METHODS`.
- Kept `shell_layout_compat.install_legacy_layout_methods()` as a stable no-op until the final removal slice can safely delete the compatibility surface.
- Updated shell compatibility tests, architecture docs, and elimination-plan progress.

Focused commands:

```bash
uv run pytest tests/test_main_window_shell_compat.py -q
# 19 passed

uv run pytest tests/test_main_window.py -q -k "spectral_progress_update or spectral_completion_finished"
# 2 passed, 109 deselected

uv run pytest tests/test_spectral_completion_worker.py -q
# 10 passed

uv run pytest tests/test_library_view_model.py -q -k spectral
# 1 passed, 2 deselected
```

The legacy layout graft map now has 0 methods.
