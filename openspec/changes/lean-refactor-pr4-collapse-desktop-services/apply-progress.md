# Apply Progress: Collapse desktop services

## Summary

- Status: apply complete; verify in progress.
- Mode: Strict TDD via existing regression suite; no assertion changes.
- Chain: PR 4 of 5, feature-branch-chain, target `tracker/lean-refactor`.

## Completed Tasks

- [x] Confirmed `recommendation_worker` and `live_assistant_state` have no production importers.
- [x] Deleted dead source modules and their tests.
- [x] Merged `scan_controller.py` + `scan_coordinator.py` into `scan_service.py`.
- [x] Merged `recommendation_controller.py` + `recommendation_coordinator.py` into `recommendation_service.py`.
- [x] Moved Live Assistant coordination into `screens/live_assistant_screen.py`.
- [x] Moved settings dialog open/apply/reset behavior into `settings_dialog.py`/`main_window.py`.
- [x] Renamed `navigation_controller.py` → `navigation.py`, `NavigationController` → `Navigation`.
- [x] Renamed `menu_builder.py` → `menu.py`, `MenuBuilder` → `Menu`.
- [x] Updated import paths in affected tests only; assertions were not changed.
- [x] Ran verify commands.

## TDD Cycle Evidence

| Task | RED | GREEN | REFACTOR |
|------|-----|-------|----------|
| Dead-code deletes | Existing suite referenced deleted modules before import updates | `uv run pytest -q` passes | Removed dead modules/tests |
| ScanService merge | Existing scan/main-window tests guarded behavior | `uv run pytest -q` passes | Collapsed controller/coordinator into one QObject service |
| RecommendationService merge | Existing recommendation/main-window tests guarded behavior | `uv run pytest -q` passes | Removed coordinator workflow re-sync hack; `MainWindow.workflow_service` setter updates owned services |
| Live Assistant move | Existing UI tests guarded signal wiring | `uv run pytest -q` passes | Moved `connect_signals`/`load_next` into screen |
| Settings move | Existing settings tests guarded apply/reset behavior | `uv run pytest -q` passes | Dialog exposes `open_dialog`, `apply`, `reset_to_defaults` |
| Renames | Existing import paths failed after rename until updated | `uv run pytest -q` passes | Renamed classes/modules without behavior change |

## Verification

- `uv run pytest -q`: pass, 848 tests.
- `uv run ruff check .`: pass.
- `uv run pyright src tests`: pass.
- `uv run python scripts/source_package_hygiene_check.py`: pass.

## Setter Counts

- `ScanService`: 3 explicit dependency setters (`set_state_accessors`, `set_ui`, `set_actions`).
- `RecommendationService`: 3 explicit dependency setters (`set_state_accessors`, `set_ui`, `set_actions`).

## Notes

- The original recommendation coordinator's in-place controller `workflow_service` re-sync was removed. The merged service owns `workflow_service`; `MainWindow.workflow_service` updates owned services when tests/runtime replace the workflow service.
- `export_coordinator.py`, `export_view_model.py`, `playlist_coordinator.py`, and `recommendation_presenter.py` were not modified.
