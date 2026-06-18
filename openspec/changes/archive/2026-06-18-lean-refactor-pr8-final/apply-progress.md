# Apply Progress: lean-refactor-pr8-final

## Mode

Strict TDD. Existing 848-test suite used as the refactor contract; no test assertions changed.

## Completed Tasks

- [x] 2. Move factory methods to `window_factory.py`.
- [x] 3. Move settings application to `SettingsController.apply_settings`.
- [x] 4. Move applied Prep Copilot variant state to `PrepCopilotController.set_applied_variant`.
- [x] 5. Move small library/player/review `_on_*` handlers to `LibraryController` and wire signals directly.
- [x] 6. Move `_LAYOUT_METHODS` and installer loop to `layout.install_layout_methods`.
- [x] 7. Remove MainWindow one-line shim method definitions and update call sites to controllers/services.
- [x] 8. Verify with pytest, ruff, pyright, and source package hygiene.

## TDD Cycle Evidence

| Task | RED | GREEN | REFACTOR |
|------|-----|-------|----------|
| 2 Factory methods | Existing 848 tests protected behavior before extraction. | `uv run pytest -q` → 848 passed. | Moved bodies to `window_factory.py`; MainWindow keeps one-line factory shims. |
| 3 Settings apply | Existing settings tests protected persistence/sync behavior. | `uv run pytest -q` → 848 passed. | `SettingsController.apply_settings` owns the logic; compatibility shim delegates. |
| 4 Prep copilot variant | Existing Prep Copilot tests protected label/state behavior. | `uv run pytest -q` → 848 passed. | `PrepCopilotController.set_applied_variant` owns variant badge updates. |
| 5 `_on_*` handlers | Existing UI/controller tests protected signal behavior. | `uv run pytest -q` → 848 passed. | Library/player/review handlers moved to `LibraryController`; signal wiring calls controller methods directly. |
| 6 Layout method installer | Existing MainWindow API tests protected dynamic methods. | `uv run pytest -q` → 848 passed. | `_LAYOUT_METHODS` moved to `layout.py`; `install_layout_methods(MainWindow)` called after class definition. |
| 7 Shim removal | Existing tests protected remaining public compatibility surface. | `uv run pytest -q` → 848 passed. | MainWindow method definitions removed; direct call sites use controllers/services. Minimal `__getattr__` compatibility remains for tested public calls. |

## Verification

- `wc -l src/xfinaudio/desktop/main_window.py` → 370 LOC.
- `uv run pytest -q` → 848 passed.
- `uv run ruff check .` → passed.
- `uv run ruff format --check .` → passed.
- `uv run pyright src tests` → passed.
- `uv run python scripts/source_package_hygiene_check.py` → passed.
- `LibraryController.__init__` parameter count → 10.
- `_LAYOUT_METHODS` installed method count from current code → 45, matching `HEAD`'s original dict count; all are callable on `MainWindow`.

## Deviations

- The prompt referred to 47 dynamically-installed layout methods, but the original `HEAD` `_LAYOUT_METHODS` dict contains 45 entries. All 45 original entries were moved and verified callable.
- Test compatibility required preserving `main_window.Qt`, `main_window.subprocess`, `window.undo()`, `window.redo()`, and `window._on_track_remove_requested(...)` behavior without reintroducing MainWindow shim method definitions.
