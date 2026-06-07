# Tasks: slim-main-window-panel-builders

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | First slice: 250-380; full constructor/page extraction likely 500+ |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 state/signal builder extraction + constructor characterization → PR 2 widget builder extraction → PR 3 central/page layout builder extraction |
| Delivery strategy | ask-on-risk |
| Chain strategy | feature-branch-chain |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: Medium

## Apply Tasks: First Slice Under 400 Changed Lines

- [x] RED/characterization: add `tests/test_main_window.py::test_main_window_constructor_exposes_initial_panel_contract` to construct `MainWindow` offscreen and verify public constructor-created controls/tables exist, expected table headers, workflow tab names/order with west tab position, and initial disabled/hidden states for scan/recommend/cancel/export/prep controls and Serato history.
- [x] RED/characterization: run `uv run pytest -q tests/test_main_window.py -k constructor_exposes_initial_panel_contract` before production refactor and keep the result as the behavior baseline; if it already passes as pure characterization, do not change production code just to force a failure.
- [x] GREEN: in `src/xfinaudio/desktop/main_window.py`, extract only constructor dependency/runtime-state initialization into private `MainWindow._initialize_window_state(scan_service, repository, settings, settings_repository)` and call it immediately after `super().__init__()`; preserve direct `self.selected_folder = self.settings.library.last_scan_folder` assignment without calling `set_selected_folder()`.
- [x] GREEN: in `src/xfinaudio/desktop/main_window.py`, extract the existing constructor signal wiring block into private `MainWindow._connect_widget_signals()` and call it after all widgets are created but before `_apply_visual_design()`; keep every signal target/lambda/table sorting connection unchanged.
- [x] TRIANGULATE: run `uv run pytest -q tests/test_main_window.py -k 'constructor_exposes_initial_panel_contract or initial or selecting_folder or recommendation_becomes_available or filtering or sorting'` and fix only regressions caused by the state/signal extraction.
- [x] REFACTOR: review `src/xfinaudio/desktop/main_window.py` diff to remove accidental duplicate constructor statements, broad reformatting, copy/layout changes, and any changes outside `MainWindow.__init__`, `_initialize_window_state`, and `_connect_widget_signals`.
- [x] VERIFY: run `uv run pytest -q`.
- [x] VERIFY: run `uv run ruff check .`.
- [x] VERIFY: run `uv run ruff format --check .`.

## Future Chain Candidates (Not Apply Tasks For This Slice)

PR 2 should extract widget creation/intrinsic widget state into `MainWindow._build_widgets()` with no layout changes. PR 3 should extract central widget/page/tab assembly into `MainWindow._build_central_widget() -> QWidget` while preserving `_apply_visual_design()` and `_apply_compact_mac_layout(...)` ordering. These future items are intentionally prose only so SDD status does not treat them as unchecked apply tasks for the first slice.
