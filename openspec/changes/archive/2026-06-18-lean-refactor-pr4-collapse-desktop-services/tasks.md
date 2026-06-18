# Tasks: Collapse desktop services

Strict TDD applies. This is a refactor with no behavioral surface; the test suite
(861 tests) is the contract. The "test" for each task is the existing regression
suite passing without modification of assertions.

## 1. Pre-flight: confirm dead-code status

- [x] `grep -rE "from xfinaudio.desktop.recommendation_worker|from xfinaudio\.desktop\.recommendation_worker|recommendation_worker\.RecommendationWorker" src/` → only the file itself and `tests/test_recommendation_worker.py`. If any production hit, STOP.
- [x] `grep -rE "from xfinaudio.desktop.live_assistant_state|from xfinaudio\.desktop\.live_assistant_state|live_assistant_state\.LiveAssistantState|live_assistant_state\.SessionTrack|live_assistant_state\.RiskAlert" src/` → only the file itself and `tests/test_live_assistant_state.py`. If any production hit, STOP.

## 2. Delete dead files

- [x] `git rm src/xfinaudio/desktop/recommendation_worker.py tests/test_recommendation_worker.py`
- [x] `git rm src/xfinaudio/desktop/live_assistant_state.py tests/test_live_assistant_state.py`

## 3. Create ScanService and update consumers

- [x] Create `src/xfinaudio/desktop/scan_service.py` with the merged `ScanService`
  class (QObject + QThread + state machine). Public API is the union of
  `ScanController` and `ScanCoordinator` methods, with explicit dependency
  setters.
- [x] `git rm src/xfinaudio/desktop/scan_controller.py src/xfinaudio/desktop/scan_coordinator.py`
- [x] Update `src/xfinaudio/desktop/main_window.py`:
  - Drop imports of `ScanController`, `ScanCoordinator`, `ScanHost`.
  - Import `ScanService` from `.scan_service`.
  - Construct `ScanService` where the pair was constructed.
  - Wire dependencies via the 4-5 explicit setters the service exposes.
  - Update call sites to use the new class name (method calls stay the same).
- [x] `grep -rE "ScanController|ScanCoordinator|ScanHost" src/ tests/` → zero hits except the change dir.

## 4. Create RecommendationService and update consumers

- [x] Create `src/xfinaudio/desktop/recommendation_service.py` with the merged
  `RecommendationService` class. Remove the in-place `workflow_service`
  re-sync hack from `recommendation_coordinator._start_recommendation_worker`
  (the constructor now owns it).
- [x] `git rm src/xfinaudio/desktop/recommendation_controller.py src/xfinaudio/desktop/recommendation_coordinator.py`
- [x] Update `main_window.py` similarly.
- [x] `grep -rE "RecommendationController|RecommendationCoordinator|RecommendationHost" src/ tests/` → zero hits.

## 5. Move LiveAssistantCoordinator into live_assistant_screen.py

- [x] Read the current `live_assistant_screen.py` to find the class.
- [x] Move the 3 methods (`connect_signals`, `load_next`) into the screen class.
- [x] Drop the `LiveAssistantHost` Protocol.
- [x] `git rm src/xfinaudio/desktop/live_assistant_coordinator.py`
- [x] Update `main_window.py`: drop the import and the field, route the screen
  signal directly.

## 6. Move SettingsController into settings_dialog.py

- [x] Read `settings_dialog.py` to find the `SettingsDialog` class.
- [x] Add `open_dialog`, `apply`, `reset_to_defaults` methods on
  `SettingsDialog`. The existing `_apply_settings` and other MainWindow-side
  helpers stay; the controller's role is to orchestrate the open/apply/reset
  flow.
- [x] Drop the `SettingsHost` Protocol.
- [x] `git rm src/xfinaudio/desktop/settings_controller.py`
- [x] Update `main_window.py`: route open/apply/reset through
  `_settings_dialog` directly.

## 7. Rename NavigationController → Navigation

- [x] `git mv src/xfinaudio/desktop/navigation_controller.py src/xfinaudio/desktop/navigation.py`
- [x] Rename class `NavigationController` → `Navigation`.
- [x] Update `main_window.py` import and usages.
- [x] Update `tests/test_navigation_controller.py` → `tests/test_navigation.py`
  and the import inside it.
- [x] `grep -rE "NavigationController" src/ tests/` → zero hits except
  history.

## 8. Rename MenuBuilder → Menu

- [x] `git mv src/xfinaudio/desktop/menu_builder.py src/xfinaudio/desktop/menu.py`
- [x] Rename class `MenuBuilder` → `Menu`.
- [x] Update `main_window.py` import and usages.
- [x] `grep -rE "MenuBuilder" src/ tests/` → zero hits.

## 9. Verify

- [x] `git ls-files` confirms the new modules and the deletions.
- [x] `uv run pytest -q` → green (all 861 tests pass with no assertion changes).
- [x] `uv run ruff check .` → green.
- [x] `uv run pyright src tests` → green.
- [x] `uv run python scripts/source_package_hygiene_check.py` → green.

## 10. Commit and merge

- [x] One work-unit commit: `refactor(desktop): collapse controller/coordinator pairs and drop dead modules`.
- [x] Push the branch.
- [x] Open PR against `tracker/lean-refactor`.
- [x] Update state.yaml → state: verifying, apply: complete.
- [x] Write apply-progress.md.
- [ ] After PR 4 merges, branch off the updated tracker for PR 5
  (`refactor/slice-mainwindow`).
