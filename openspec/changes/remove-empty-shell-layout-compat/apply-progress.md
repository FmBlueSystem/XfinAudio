# Apply Progress: Remove empty shell layout compatibility surface

Status: verified

## RED

Command:

```bash
uv run pytest tests/test_main_window_shell_compat.py::test_layout_compat_graft_surface_is_removed -q
```

Result: failed as expected because `main_window.py` still imported `shell_layout_compat` and called `install_legacy_layout_methods`.

## GREEN

Changes:
- Removed `shell_layout_compat` import and install call from `main_window.py`.
- Deleted `src/xfinaudio/desktop/shell_layout_compat.py`.
- Removed layout graft reexports from `shell_compat.py`.
- Updated shell compatibility tests to assert the layout graft surface is gone and explicit `MainWindow` methods remain callable.
- Updated architecture docs and current specs.

Focused commands:

```bash
uv run pytest tests/test_main_window_shell_compat.py -q
# 19 passed

uv run pytest tests/test_main_window.py -q
# 111 passed

uv run pyright src tests
# 0 errors

uv run ruff check .
# passed
```
