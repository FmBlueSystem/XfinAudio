# Design: Slice main_window.py (partial)

## Approach

Ten mechanical extractions from `main_window.py` into their own modules. Each
extraction is class-scoped or function-scoped, takes its dependencies explicitly
(via constructor or function arguments), and preserves the exact same public
behavior. The existing 848-test suite is the contract; no new tests, no
assertion changes.

## Public API preservation rules

For each extraction:
- The extracted class or function takes the same dependencies as the original
  MainWindow method (widgets, view models, services, callbacks).
- The MainWindow method becomes a one-line delegation.
- No call site in `main_window.py`, the coordinators, the services, or the
  tests needs to change other than the import.

## Files affected

### New files (10)

| Path | LOC target | Source |
|------|------------|--------|
| `src/xfinaudio/desktop/layout.py` | ~25 | `responsive_sidebar_width` (17 LOC + imports) |
| `src/xfinaudio/desktop/workflow_stack.py` | ~35 | `WorkflowStack` class (28 LOC + imports) |
| `src/xfinaudio/desktop/undo_toolbar.py` | ~60 | `_build_undo_toolbar` + `undo`/`redo`/`_refresh_undo_state` (36 LOC + class boilerplate) |
| `src/xfinaudio/desktop/shortcuts.py` | ~50 | `_connect_keyboard_shortcuts` (25 LOC + helper boilerplate) |
| `src/xfinaudio/desktop/responsive.py` | ~60 | `resizeEvent` + `_apply_responsive_layout` + `set_full_screen` (35 LOC) |
| `src/xfinaudio/desktop/visual_design.py` | ~120 | `_apply_compact_mac_layout` + `_apply_compact_table_columns` + `_apply_visual_design` (110 LOC) |
| `src/xfinaudio/desktop/table_sorting.py` | ~40 | `_connect_table_sorting` + `_sort_table_by_column` (22 LOC) |
| `src/xfinaudio/desktop/prep_copilot.py` | ~150 | `generate_prep_copilot` + `apply_selected_prep_copilot_variant` + `_apply_prep_copilot_item` + `_on_copilot_variant_applied` (130 LOC) |
| `src/xfinaudio/desktop/recommendation_render.py` | ~150 | `show_recommendation` + `clear_recommendation_review` + `show_transition_review` (130 LOC) |
| `src/xfinaudio/desktop/export_actions.py` | ~120 | 8 export method thin wrappers (110 LOC) |

### Modified files (3)

| Path | Change |
|------|--------|
| `src/xfinaudio/desktop/main_window.py` | -750 LOC, +50 LOC of delegating shims → net -700 LOC |
| `src/xfinaudio/desktop/app_state.py` | +5 LOC (`SettingsPersistence` Protocol added) |
| `tests/test_main_window.py` | MAY need an import update if any test directly imports the moved names; assertions MUST NOT change |

### Public API of the new modules

```python
# layout.py
def responsive_sidebar_width(window_width: int) -> int: ...

# workflow_stack.py
class WorkflowStack(QStackedWidget):
    def tabText(self, index: int) -> str: ...
    def setTabEnabled(self, index: int, enabled: bool) -> None: ...
    def isTabEnabled(self, index: int) -> bool: ...
    def setCurrentIndex(self, index: int) -> None: ...
    # currentChanged signal is inherited

# undo_toolbar.py
class UndoToolbar:
    def __init__(self, undo_manager: UndoManager, parent: QWidget) -> None: ...
    @property
    def toolbar(self) -> QToolBar: ...
    def undo(self) -> None: ...
    def redo(self) -> None: ...

# shortcuts.py
def bind_main_window_shortcuts(window: QMainWindow) -> dict[str, QShortcut]: ...

# responsive.py
class ResponsiveLayout:
    def __init__(self, sidebar_panel, sidebar_list, label_list) -> None: ...
    def apply(self, window_width: int) -> None: ...
    def set_full_screen(self, enabled: bool) -> None: ...

# visual_design.py
def apply_visual_design(window) -> None: ...

# table_sorting.py
def connect_table_sorting(table, sort_orders, on_library_resort) -> None: ...

# prep_copilot.py
class PrepCopilotController:
    def __init__(self, *, build_screen, build_vm, state, workflow_service, on_state_changed, on_status_message) -> None: ...
    def generate(self) -> None: ...
    def apply_selected_variant(self) -> None: ...
    def apply_item(self, item) -> None: ...
    def on_variant_applied(self, variant_name) -> None: ...

# recommendation_render.py
def render_recommendation(*, review_screen, library_vm, build_vm, review_vm, state, view_models, tr) -> None: ...
def clear_recommendation_review(*, review_screen, status_label, message, tr) -> None: ...
def show_transition_review(*, review_screen, explanation, tr) -> None: ...

# export_actions.py
class ExportActions:
    def __init__(self, export_coordinator) -> None: ...
    def preview_export(self) -> None: ...
    def export_recommendation(self) -> None: ...
    def preview_serato_export(self) -> None: ...
    def export_recommendation_to_serato(self) -> None: ...
    def export_metadata_status_to_serato(self) -> None: ...
    def export_dj_readiness_report(self) -> None: ...
    def choose_safe_export_folder(self) -> None: ...
    def set_safe_export_folder(self, folder) -> None: ...
```

## MainWindow shims

Each extracted method on `MainWindow` becomes a thin delegating wrapper:

```python
# before
def undo(self) -> None:
    self._undo_manager.undo()
    self._refresh_undo_state()

# after
def undo(self) -> None:
    self._undo_toolbar.undo()
```

The point of the shim is to keep the signal-wiring sites (`self.undo_button.clicked.connect(self.undo)`)
unchanged, so `_connect_widget_signals` does not need to change.

## Step-by-step

1. Pre-flight: `git status` clean; all 848 tests pass.
2. Create `layout.py` with `responsive_sidebar_width`. Update `main_window.py`
   to import it. Run `pytest tests/test_main_window.py -q`. Green.
3. Create `workflow_stack.py` with `WorkflowStack`. Update `main_window.py`.
   Run pytest. Green.
4. Move `SettingsPersistence` Protocol to `app_state.py`. Update
   `main_window.py`. Run pytest. Green.
5. Create `undo_toolbar.py` with `UndoToolbar`. Update `main_window.py`'s
   `_initialize_window_state` to construct it, and replace the three undo
   methods with one-line shims. Run pytest. Green.
6. Create `shortcuts.py` with `bind_main_window_shortcuts`. Replace
   `_connect_keyboard_shortcuts` with a call to it. Run pytest. Green.
7. Create `responsive.py` with `ResponsiveLayout`. Wire it in
   `_initialize_window_state`. Replace `resizeEvent` and
   `_apply_responsive_layout` with delegations. Run pytest. Green.
8. Create `visual_design.py` with `apply_visual_design`. Replace the three
   visual methods. Run pytest. Green.
9. Create `table_sorting.py` with `connect_table_sorting`. Replace
   `_connect_table_sorting` and `_sort_table_by_column` with a small shim
   that calls the helper. Run pytest. Green.
10. Create `prep_copilot.py` with `PrepCopilotController`. Wire it in
    `_initialize_window_state`. Replace the four prep-copilot methods with
    delegations. Run pytest. Green.
11. Create `recommendation_render.py` with the three render functions. Replace
    the three render methods. Run pytest. Green.
12. Create `export_actions.py` with `ExportActions`. Wire it in
    `_initialize_window_state`. Replace the 8 export methods with
    delegations. Run pytest. Green.
13. Run full verify: pytest (all 848), ruff, pyright, hygiene check.
14. Single work-unit commit: `refactor(desktop): slice main_window into 10 helper modules`.
15. Push. Open PR against `tracker/lean-refactor`.

## Risks

- **Signal handler signatures**: each shim must accept the same arguments as
  the original method because the wiring in `_connect_widget_signals` uses
  `connect(self.undo)` etc. If a signature changes, every connect site must
  change too.
- **Shared state across extractions**: the prep-copilot controller, the
  recommendation renderer, and the export actions all read or write
  `MainWindow`'s state via the property accessors. These stay on
  `MainWindow`; the new modules receive the state via constructor injection.
- **Test imports**: `tests/test_main_window.py` may import from the moved
  modules directly. The apply step MUST grep for moved names and update
  the test imports.
- **Visual design side effects**: `_apply_compact_mac_layout` sets widths
  and policies on widgets that `_apply_compact_table_columns` then
  re-uses. The combined function must be order-preserving.

## Rollback

Single `git revert <commit-sha>` restores the previous state.
