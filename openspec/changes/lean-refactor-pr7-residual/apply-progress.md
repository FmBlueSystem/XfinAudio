# Apply Progress: lean-refactor-pr7-residual

## Mode

Strict TDD. Existing regression suite is the contract for each refactor step; no test assertions were changed.

## Completed Tasks

- [x] 2. Added missing runtime attributes to `AppState` while preserving existing public state names.
- [x] 3. Added `_APP_STATE_ATTRIBUTES`, `__getattr__`, and `__setattr__` compatibility shims to `MainWindow`.
- [x] 4. Removed the 15 explicit `MainWindow` property accessors.
- [x] 5. Moved signal wiring into per-screen `connect_signals(window)` methods and replaced `_connect_widget_signals` with `_connect_screens`.
- [x] 6. Exposed `build_main_window_layout(window)` and `build_main_widgets(window)` in `layout.py`; `MainWindow` keeps one-line layout shims.
- [x] 7. Created `window_factory.initialize_window_state(...)` and made `MainWindow._initialize_window_state` a shim.
- [x] 8. Verified tests, lint, typing, hygiene, new file presence, and `main_window.py` LOC budget.

## TDD Cycle Evidence

| Task | RED | GREEN | REFACTOR |
|------|-----|-------|----------|
| 2. AppState attributes | Existing 848-test suite protects compatibility. | `uv run pytest -q` passed: 848. | Added only missing direct state fields. |
| 3. MainWindow dunder shim | Existing 848-test suite caught workflow-service setter regression. | `uv run pytest -q` passed: 848 after setter sync fix. | Kept shim limited to the 15 former property names. |
| 4. Remove properties | Existing 848-test suite caught scan-token compatibility regression. | `uv run pytest -q` passed: 848 after state/service synchronization fix. | Removed all 15 property definitions. |
| 5. Screen signal wiring | Existing 848-test suite protects signal behavior. | `uv run pytest -q` passed: 848. | Each screen owns its window-facing signal wiring. |
| 6. Layout extraction | Existing 848-test suite protects window construction. | `uv run pytest -q` passed: 848. | `layout.py` owns `build_main_window_layout` and widget helpers. |
| 7. Window factory | Existing 848-test suite protects construction and controllers. | `uv run pytest -q` passed: 848. | `window_factory.py` owns service/view-model/controller construction. |

## Verification

- `wc -l src/xfinaudio/desktop/main_window.py`: 690
- `uv run pytest -q`: 848 passed
- `uv run ruff check .`: passed
- `uv run pyright src tests`: passed
- `uv run python scripts/source_package_hygiene_check.py`: passed

## Files Changed

- `src/xfinaudio/desktop/app_state.py`
- `src/xfinaudio/desktop/main_window.py`
- `src/xfinaudio/desktop/layout.py`
- `src/xfinaudio/desktop/window_factory.py`
- `src/xfinaudio/desktop/screens/library_screen.py`
- `src/xfinaudio/desktop/screens/build_screen.py`
- `src/xfinaudio/desktop/screens/review_screen.py`
- `src/xfinaudio/desktop/screens/export_screen.py`
- `src/xfinaudio/desktop/screens/metadata_screen.py`
- `src/xfinaudio/desktop/screens/my_playlists_screen.py`
- `src/xfinaudio/desktop/screens/playlist_editor.py`
- `src/xfinaudio/desktop/screens/live_assistant_screen.py`

## Deviations

- To satisfy the hard `<700 LOC` target, additional already-delegating `MainWindow` methods were bound from `layout.py` instead of remaining as class-body boilerplate. Behavior stayed covered by the unchanged 848-test suite.
