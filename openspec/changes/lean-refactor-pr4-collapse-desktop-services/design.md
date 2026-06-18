# Design: Collapse desktop services

## Approach

Two dead-code deletes, two parallel-file merges, and four single-caller moves.
Each change is mechanical and the test suite is the contract. The merge is done
class-by-class with explicit public-API preservation.

## Public API preservation rules

For each merge or move, the public method names and signatures of the surviving
class MUST equal the union of the public methods of the merged classes. The
`MainWindow` call sites are updated only to point at the new class names; method
calls stay byte-identical.

## Files affected

### Deletes (6)

| Path                                                       | LOC | Notes |
|------------------------------------------------------------|-----|-------|
| `src/xfinaudio/desktop/recommendation_worker.py`           | 54  | dead in production |
| `src/xfinaudio/desktop/live_assistant_state.py`            | 167 | dead in production |
| `tests/test_recommendation_worker.py`                      | ?   | test of dead code   |
| `tests/test_live_assistant_state.py`                       | ?   | test of dead code   |
| `src/xfinaudio/desktop/scan_controller.py`                 | 119 | merged into scan_service |
| `src/xfinaudio/desktop/scan_coordinator.py`                | 181 | merged into scan_service |
| `src/xfinaudio/desktop/recommendation_controller.py`       | 95  | merged into recommendation_service |
| `src/xfinaudio/desktop/recommendation_coordinator.py`      | 180 | merged into recommendation_service |
| `src/xfinaudio/desktop/live_assistant_coordinator.py`      | 56  | moved into live_assistant_screen |
| `src/xfinaudio/desktop/settings_controller.py`             | 68  | moved into settings_dialog |
| `src/xfinaudio/desktop/navigation_controller.py`           | 80  | renamed to navigation.py |
| `src/xfinaudio/desktop/menu_builder.py`                    | 93  | renamed to menu.py |

### New modules (2)

| Path                                                  | LOC target | Source |
|-------------------------------------------------------|------------|--------|
| `src/xfinaudio/desktop/scan_service.py`               | ~290       | scan_controller + scan_coordinator merged |
| `src/xfinaudio/desktop/recommendation_service.py`     | ~260       | recommendation_controller + recommendation_coordinator merged |

### Renames (2)

| From                                                | To                                    |
|-----------------------------------------------------|---------------------------------------|
| `src/xfinaudio/desktop/navigation_controller.py`    | `src/xfinaudio/desktop/navigation.py`  |
| `src/xfinaudio/desktop/menu_builder.py`             | `src/xfinaudio/desktop/menu.py`       |

## Public API of the new `ScanService`

```python
class ScanService(QObject):
    scan_progress_updated = Signal(object)
    scan_completed = Signal(object)
    scan_failed = Signal(object)
    worker_cleared = Signal()

    def __init__(self, workflow_service, *, parent=None): ...
    def start_scan(self, folder, token): ...           # was ScanController.start_scan
    def cancel(self): ...                              # was ScanController.cancel
    # New: state-machine methods (were ScanCoordinator)
    def scan_selected_folder(self): ...                 # was ScanCoordinator.scan_selected_folder
    def begin_scan_state(self): ...                     # was ScanCoordinator.begin_scan_state
    def on_completed(self, result): ...                # was ScanCoordinator.on_completed (Slot)
    def on_failed(self, error): ...                     # was ScanCoordinator.on_failed (Slot)
    def on_progress(self, progress): ...                # was ScanCoordinator.on_progress
    def cancel_scan(self): ...                          # was ScanCoordinator.cancel
```

The old `ScanCoordinator` accessed many private members of `MainWindow` (`_pre_scan_records_by_path`,
`_state`, `_scan_controller`, `_library_screen`, `_build_screen`, etc.). The new
`ScanService` keeps these as private state inside the service and exposes
explicit setter methods that `MainWindow` calls from the existing entry points.
This is the one place where the public surface changes meaningfully: the
"Protocol with one implementation" is replaced by explicit dependency wiring.

Specifically:
- `host.selected_folder` is passed into `scan_selected_folder(selected_folder)` as
  an explicit argument.
- `host.scanned_records`, `host._pre_scan_records_by_path`, `host._state` become
  `ScanService` private state, set via `set_library_state(scanned_records,
  pre_scan_by_path, state)`.
- `host._library_screen`, `host._build_screen` are passed into the begin/end
  state methods that need to enable/disable buttons.
- `host.status_label`, `host.scan_progress_label`,
  `host.recommendation_guidance_label`, `host.library_guidance_label` are passed
  as a `ScanUI` small Protocol OR as `set_ui(status_label, scan_progress_label,
  ...)`.

The design prefers **explicit setters over Protocols** to avoid recreating the
same YAGNI this PR is removing. The service exposes 4-5 small setters and the
caller (`MainWindow`) wires them once at construction.

## Public API of the new `RecommendationService`

Same pattern: union of `RecommendationController` and `RecommendationCoordinator`
methods, with explicit dependency wiring. The progress/coordinator signal
handlers become slot methods on the service.

## `live_assistant_coordinator.py` merge into `live_assistant_screen.py`

The `LiveAssistantCoordinator` (56 LOC) is a 3-method thin wrapper: `connect_signals`,
`load_next`. The screen already has its own constructor. The merge moves the 3
methods into the screen class directly, dropping the `LiveAssistantHost` Protocol.

## `settings_controller.py` merge into `settings_dialog.py`

Same pattern: the `SettingsDialog` (in `settings_dialog.py`) gets the
`open_dialog`, `apply`, `reset_to_defaults` methods directly. The
`SettingsHost` Protocol is dropped.

## Renames (no behavior change)

- `navigation_controller.NavigationController` → `navigation.Navigation`
- `menu_builder.MenuBuilder` → `menu.Menu` (with `build` and `show_about_dialog`
  unchanged)

## `MainWindow` updates

`MainWindow` is updated to:

1. Import `ScanService` instead of `ScanController` + `ScanCoordinator`.
2. Import `RecommendationService` instead of `RecommendationController` +
   `RecommendationCoordinator`.
3. Drop imports of `LiveAssistantCoordinator` and `SettingsController`.
4. Update `NavigationController` import to `navigation.Navigation`.
5. Update `MenuBuilder` import to `menu.Menu`.
6. Construct the new services in the same place the old ones were constructed.
7. Wire the new services to the existing widgets via explicit setters (only
   for `ScanService` and `RecommendationService`).
8. The size of `main_window.py` MAY decrease by a small amount (the import
   list shrinks; the constructor shrinks; the call sites stay byte-identical
   except for the class names).

**`main_window.py` is NOT sliced in this PR.** Slicing it is PR 5. This PR
only updates its imports and class names.

## Step-by-step

1. Pre-flight grep: confirm `recommendation_worker` and `live_assistant_state`
   have zero production importers; if any appear, STOP and report.
2. Delete the 4 dead files (2 source + 2 tests).
3. Create `scan_service.py` with the merged class. Delete `scan_controller.py`
   and `scan_coordinator.py`.
4. Update `main_window.py`: replace `ScanController` + `ScanCoordinator`
   references with `ScanService`. Wire dependencies via setters.
5. Update tests that import from `scan_controller` / `scan_coordinator`
   (likely none, but verify).
6. Run targeted tests: `uv run pytest tests/test_main_window.py -q`.
7. Repeat 3-6 for `recommendation_service.py`.
8. Move `live_assistant_coordinator.py` into `screens/live_assistant_screen.py`.
9. Move `settings_controller.py` into `settings_dialog.py`.
10. Rename `navigation_controller.py` → `navigation.py`. Update
    `NavigationController` → `Navigation`. Update imports.
11. Rename `menu_builder.py` → `menu.py`. Update `MenuBuilder` → `Menu`. Update
    imports.
12. Run full verify: pytest, ruff, pyright.
13. Commit.

## Risks

- **`ScanService` setter explosion**: if the service needs 10+ setters, we are
  recreating the Protocol. The design limit is 5 setters. If exceeded, the
  apply step MUST revisit and either accept a small `ScanUI` Protocol or split
  the service into smaller pieces.
- **Test imports**: the test files for the moved/merged modules need their
  imports updated. The apply step MUST grep for imports of the deleted module
  names and update them.
- **`recommendation_coordinator` calls `_recommendation_controller.workflow_service`
  in-place** to re-sync the workflow service. The merged service owns the
  workflow service in `__init__`, so this hack can be removed; the apply step
  MUST remove the in-place assignment and update the test that covers it (if
  any).

## Rollback

Single `git revert <commit-sha>` restores the previous state.
