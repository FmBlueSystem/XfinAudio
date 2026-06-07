# Technical Design: slim-main-window-widget-builders

## Goal

Extract only `MainWindow.__init__` widget construction and intrinsic widget configuration into a private `MainWindow._build_widgets() -> None` method while preserving the desktop window contract. This is a behavior-preserving refactor for `src/xfinaudio/desktop/main_window.py`; it does not change app startup, workers, table populators, labels/copy, product flows, or layout/page assembly.

## Current state

`MainWindow.__init__` currently performs:

1. `super().__init__()`.
2. `_initialize_window_state(...)` for dependencies, settings, and runtime state.
3. Inline widget creation/configuration: title, public widget attributes, labels, buttons, filters, tables, headers, selection modes, enabled/visible defaults, and label sizing.
4. `_connect_widget_signals()` for most signal wiring and table sorting.
5. `_apply_visual_design()`.
6. Inline controls/page/tab/central-widget layout assembly and `_apply_compact_mac_layout(...)`.

This change extracts step 3 only. The existing `tracks_table.itemSelectionChanged.connect(self._refresh_idle_action_state)` line is signal wiring and should move into `_connect_widget_signals()` rather than remain in the new widget builder.

## Design decisions

- Add a private method on `MainWindow`; do not add a public builder class, helper module, dataclass carrier, or new import path.
- Keep `MainWindow.__init__` as the constructor orchestrator and preserve its public signature.
- Move existing widget statements mechanically; avoid copy, label, workflow, table, styling, or layout behavior changes.
- Keep all public widget attribute names unchanged.
- Keep layout/page/tab/central-widget assembly inline in `__init__` for PR3.
- Keep all signal wiring in `_connect_widget_signals()`.
- Keep `_build_widgets()` after `_initialize_window_state(...)` because `safe_export_folder_label` depends on initialized settings.
- Keep `_build_widgets()` before `_connect_widget_signals()` and `_apply_visual_design()` because both require constructed widget attributes.

## Method boundaries

### `MainWindow.__init__(...) -> None`

New orchestration order:

1. `super().__init__()`
2. `self._initialize_window_state(scan_service, repository, settings, settings_repository)`
3. `self._build_widgets()`
4. `self._connect_widget_signals()`
5. `self._apply_visual_design()`
6. existing inline layout/page/tab assembly, unchanged
7. `self._apply_compact_mac_layout(...)`, unchanged
8. existing central widget installation, unchanged

### `MainWindow._build_widgets(self) -> None`

Move the current inline widget construction/configuration block into this method, including:

- `setWindowTitle("XfinAudio")`
- scan buttons and initial enabled states
- folder/status/guidance/decision labels
- safe export controls and label text from `_format_safe_export_folder_label()`
- Serato/readiness buttons and disabled defaults
- search/filter controls and metadata status export button
- `tracks_table` creation, headers, `SelectRows` behavior, `ExtendedSelection` mode
- strategy/recommendation controls
- Prep Copilot inputs/buttons/table, headers, `SelectRows` behavior, `SingleSelection` mode
- recommendation/review/readiness/transition/export-history tables and headers
- `serato_export_history_table.setVisible(False)`
- label word-wrap, width, and max-height constraints

Do **not** include signal connections or layout assembly.

### `MainWindow._connect_widget_signals(self) -> None`

Keep existing connections and add the relocated line:

- `self.tracks_table.itemSelectionChanged.connect(self._refresh_idle_action_state)`

No signal target or product behavior changes.

## Data flow and construction contract

1. Caller constructs `MainWindow` through the existing import path and keyword signature.
2. `_initialize_window_state(...)` stores services/settings and initializes runtime fields.
3. `_build_widgets()` creates all public Qt widget attributes and intrinsic configuration.
4. `_connect_widget_signals()` wires buttons, filters, table selection refresh, double-click handling, exports, and table sorting.
5. `_apply_visual_design()` applies object names and table render defaults.
6. Inline layout assembly attaches the same widgets to the same pages/tabs and central widget.

Public compatibility remains unchanged: existing tests/callers can access the same `MainWindow` widget attributes and wrapper methods.

## Files to change

- `src/xfinaudio/desktop/main_window.py`
  - Replace the inline widget block in `__init__` with `self._build_widgets()`.
  - Add private `_build_widgets()` near `_initialize_window_state()` / `_connect_widget_signals()`.
  - Move `tracks_table.itemSelectionChanged` connection into `_connect_widget_signals()`.
- `tests/test_main_window.py`
  - Add focused offscreen characterization for `tracks_table` and `prep_copilot_table` selection behavior/mode if not already present.
- `openspec/changes/slim-main-window-widget-builders/design.md`
  - This design artifact.

Files explicitly not changed:

- `src/xfinaudio/desktop/app.py`
- `src/xfinaudio/desktop/table_populators.py`
- `src/xfinaudio/desktop/_workers.py`
- domain/export/recommendation/library behavior modules

## Test plan

Strict TDD command: `uv run pytest -q`.

1. Red/characterization first: add or extend an offscreen constructor test asserting:
   - `tracks_table.selectionBehavior() == QAbstractItemView.SelectionBehavior.SelectRows`
   - `tracks_table.selectionMode() == QAbstractItemView.SelectionMode.ExtendedSelection`
   - `prep_copilot_table.selectionBehavior() == QAbstractItemView.SelectionBehavior.SelectRows`
   - `prep_copilot_table.selectionMode() == QAbstractItemView.SelectionMode.SingleSelection`
2. Perform the extraction.
3. Run validation:
   - `uv run pytest -q`
   - `uv run ruff check .`
   - `uv run ruff format --check .`

Existing `tests/test_main_window.py` coverage already protects title/copy, table headers, tab contract, initial enabled/hidden states, saved settings, selection-driven recommendation enablement, filtering, sorting, review, export, and Prep Copilot flows.

## Review budget and rollout

Keep the first implementation slice under 400 changed lines. The intended diff is a mechanical move in `main_window.py` plus a small optional test addition. Roll out as a normal internal refactor PR with no migration, feature flag, or staged runtime behavior.

## Risks and mitigations

- **Widget used before creation:** fixed by constructor order: initialize state, build widgets, connect signals, apply visual design, then assemble layout.
- **Lost public widget attribute/header/state:** move statements mechanically and rely on constructor characterization tests.
- **Signal duplicated or lost:** remove `itemSelectionChanged` from the widget block and add it exactly once in `_connect_widget_signals()`.
- **Scope creep into PR3:** leave page/tab/central layout assembly in `__init__`.
- **Product/UX drift:** do not edit copy, labels, layouts, flows, workers, table populators, or app entrypoint.

## Rollback

Revert the `_build_widgets()` extraction, the relocated signal connection, and any added characterization test. No settings, schema, data, worker, entrypoint, or product-flow rollback is required.
