# Apply Progress: lean-refactor-pr6-slice-shell

## Status

Partial — tasks 2-5 were implemented and the regression suite is green, but final verify is blocked because `main_window.py` is still 1033 LOC (>600).

## Completed Tasks

- [x] Task 2 — extracted `AppController`.
- [x] Task 3 — extracted `LibraryController`.
- [x] Task 4 — extracted `SettingsController`.
- [x] Task 5 — extracted `DjReadinessController`.

## TDD Cycle Evidence

| Task | RED | GREEN | REFACTOR |
|------|-----|-------|----------|
| 2 | Existing 848-test suite is the regression contract; no assertions changed. | `uv run pytest -q` eventually passed. | State/render orchestration moved to `AppController`; shims retained. |
| 3 | Existing 848-test suite caught shim and AppState identity regressions. | `uv run pytest -q` passed after preserving monkeypatch seams and immutable state replacement. | Library/table/filter/spectral logic moved to `LibraryController`. |
| 4 | Existing settings tests caught `_MockHost` compatibility. | `uv run pytest -q` passed after preserving fallback behavior. | Settings dialog/apply logic moved to `SettingsController`. |
| 5 | Existing readiness/export tests covered readiness rendering. | `uv run pytest -q` passed. | DJ readiness rendering moved to `DjReadinessController`. |

## Verification Results

- `uv run pytest -q` — PASS, 848 passed.
- `uv run ruff check .` — PASS.
- `uv run pyright src tests` — PASS.
- `uv run python scripts/source_package_hygiene_check.py` — PASS.
- `wc -l src/xfinaudio/desktop/main_window.py` — FAIL, 1033 LOC (must be <600).
- `git ls-files` for new files — not run as pass condition because files are not committed/tracked yet.

## Files Changed

- `src/xfinaudio/desktop/app_controller.py` — new state sync/render controller.
- `src/xfinaudio/desktop/library_controller.py` — new library/filter/spectral controller.
- `src/xfinaudio/desktop/settings_controller.py` — new settings dialog controller.
- `src/xfinaudio/desktop/dj_readiness_controller.py` — new DJ readiness controller.
- `src/xfinaudio/desktop/main_window.py` — constructs controllers and delegates extracted methods.

## Deviations

- Controllers use small dataclass dependency bundles to stay under the 15-constructor-parameter hard limit.
- `AppController` is initialized after layout construction because `workflow_tabs` and `workflow_sidebar` do not exist in `_initialize_window_state`.
- `LibraryController` is initialized after widget construction because labels/buttons do not exist in `_initialize_window_state`.

## Blocker

The requested 4 extractions did not reduce `main_window.py` below 600 LOC in this branch. More body moves or a broader shell split are required before commit/push/PR.
