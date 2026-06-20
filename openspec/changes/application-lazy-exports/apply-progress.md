# Apply progress: application-lazy-exports

## Status
Applied.

## RED
- `uv run pytest tests/test_application_package_import_boundaries.py -q`
- Failed as expected because importing `xfinaudio.application.saved_playlists` loaded sibling modules through eager package exports:
  - `xfinaudio.application.playlist_workflow`
  - `xfinaudio.application.vertical_playlist_flow`

## GREEN
- Converted `xfinaudio.application.__init__` to lazy public exports with `_EXPORTS`, `__getattr__`, stable `__all__`, and `TYPE_CHECKING` imports.

## Focused evidence
- `uv run pytest tests/test_application_package_import_boundaries.py tests/test_application_vertical_playlist_flow.py tests/test_playlist_workflow.py tests/test_application_saved_playlists.py -q` -> 14 passed.
- `uv run pyright src/xfinaudio/application/__init__.py tests/test_application_package_import_boundaries.py` -> 0 errors, 0 warnings.
- `uv run ruff check ...` and `uv run ruff format --check ...` -> pass.
