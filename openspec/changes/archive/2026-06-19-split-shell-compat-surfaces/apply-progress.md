# Apply Progress: Split Shell Compatibility Surfaces

## Status
Implementation complete; verification in progress.

## RED
`uv run pytest tests/test_main_window_shell_compat.py::test_shell_compat_surfaces_are_split_by_responsibility -q` failed because `shell_layout_compat` and `shell_state_compat` did not exist.

## GREEN
Created `xfinaudio.desktop.shell_layout_compat` for layout method compatibility and `xfinaudio.desktop.shell_state_compat` for AppState read/write compatibility.

## Refactor
Reduced `xfinaudio.desktop.shell_compat` to a thin facade that re-exports the existing compatibility names while new code can use narrower surfaces.

## Documentation
Updated `docs/architecture/layered-architecture.md` so Slice 5 records the compatibility surface split and the remaining work shifts from splitting to shrinking/removing surfaces.
