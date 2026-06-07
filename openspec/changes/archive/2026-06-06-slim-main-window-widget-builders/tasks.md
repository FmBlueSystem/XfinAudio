# Tasks: slim-main-window-widget-builders

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 180-260 (same-file widget block move + one relocated signal + focused characterization test) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR for this PR2 widget-builder slice; defer PR3 central/page/tab layout builder work to a future change |
| Delivery strategy | auto-chain |
| Chain strategy | feature-branch-chain |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: feature-branch-chain
400-line budget risk: Low
applyState: ready
allowedEditRoots:
- `src/xfinaudio/desktop/main_window.py`
- `tests/test_main_window.py`
- `openspec/changes/slim-main-window-widget-builders/`

## Apply Boundary

This slice is limited to `src/xfinaudio/desktop/main_window.py`, `tests/test_main_window.py`, and this OpenSpec change directory. Do not edit `src/xfinaudio/desktop/app.py`, `src/xfinaudio/desktop/table_populators.py`, `src/xfinaudio/desktop/_workers.py`, export/recommendation/library domain modules, product copy, workflow behavior, styling, or layout/page/tab assembly.

## Implementation Tasks

- [x] RED/characterization: add or extend an offscreen constructor test in `tests/test_main_window.py` (for example `test_main_window_table_selection_configuration`) that imports or references `QAbstractItemView` and asserts `tracks_table.selectionBehavior() == QAbstractItemView.SelectionBehavior.SelectRows`, `tracks_table.selectionMode() == QAbstractItemView.SelectionMode.ExtendedSelection`, `prep_copilot_table.selectionBehavior() == QAbstractItemView.SelectionBehavior.SelectRows`, and `prep_copilot_table.selectionMode() == QAbstractItemView.SelectionMode.SingleSelection` on a freshly constructed `MainWindow`.
- [x] RED/characterization: run `uv run pytest -q tests/test_main_window.py -k table_selection_configuration` before production edits and keep the result as the characterization baseline; if it passes against current code, continue without forcing an artificial failure because this is a behavior-preserving refactor.
- [x] GREEN: in `src/xfinaudio/desktop/main_window.py`, add private `MainWindow._build_widgets(self) -> None` near `_initialize_window_state()` and move the current inline widget creation/configuration block into it, including `setWindowTitle`, all public widget attribute assignments, headers, selection behavior/mode, enabled/visible defaults, placeholders, and label word-wrap/width/height constraints.
- [x] GREEN: in `src/xfinaudio/desktop/main_window.py`, replace the moved inline block in `MainWindow.__init__` with `self._build_widgets()` immediately after `self._initialize_window_state(...)` and before `self._connect_widget_signals()`, leaving `_apply_visual_design()`, layout/page/tab assembly, `_apply_compact_mac_layout(...)`, and `setCentralWidget(...)` order unchanged.
- [x] GREEN: in `src/xfinaudio/desktop/main_window.py`, move `self.tracks_table.itemSelectionChanged.connect(self._refresh_idle_action_state)` into `_connect_widget_signals()` exactly once so `_build_widgets()` contains no signal wiring.
- [x] TRIANGULATE: run `uv run pytest -q tests/test_main_window.py -k 'constructor_exposes_initial_panel_contract or constructs_desktop_scanning_skeleton or initial or empty_state_guidance or table_selection_configuration or selection or idle_action'` and fix only regressions caused by the widget extraction or relocated connection.
- [x] REFACTOR: review `src/xfinaudio/desktop/main_window.py` to confirm the extraction is mechanical: no duplicated or dropped widget statements, no product copy/style/layout changes, no layout/page/tab extraction, and no production edits outside `__init__`, `_build_widgets()`, and `_connect_widget_signals()`.
- [x] REFACTOR: verify preserved initial-state dependencies in `src/xfinaudio/desktop/main_window.py`: `_initialize_window_state(...)` still runs before `_build_widgets()`, `safe_export_folder_label` still uses `_format_safe_export_folder_label()`, and `serato_export_history_table.setVisible(False)` remains part of widget configuration.
- [x] VERIFY: run `uv run pytest -q`.
- [x] VERIFY: run `uv run ruff check .`.
- [x] VERIFY: run `uv run ruff format --check .`.
- [x] VERIFY: inspect the final diff with `git diff --stat` and `git diff -- src/xfinaudio/desktop/main_window.py tests/test_main_window.py`; if the diff approaches 400 changed lines or includes PR3 layout/page extraction, stop and ask for delivery guidance before continuing.

## Future / Deferred Work

PR3 central/page/tab layout builder work is intentionally not an apply task for this change. A later change may extract central widget and page/tab assembly into a private builder while preserving `_apply_visual_design()` and `_apply_compact_mac_layout(...)` ordering and Qt layout ownership.
