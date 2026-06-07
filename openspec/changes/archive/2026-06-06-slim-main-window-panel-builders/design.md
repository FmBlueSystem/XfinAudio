# Technical Design: slim-main-window-panel-builders

## Overview

Refactor `xfinaudio.desktop.main_window.MainWindow.__init__` from one large constructor into a small constructor orchestrator plus private builder methods on `MainWindow`. This is a behavior-preserving desktop UI maintainability slice: no product flow, copy, layout, worker, table-populator, app entrypoint, persistence, or export behavior changes.

The design keeps Qt ownership simple by assigning all constructor-created widgets to `self` exactly as today and by building layouts in private methods on the existing `MainWindow` instance. No new public builder API, helper module, dataclass carrier, or factory import path is introduced.

## Current code summary

`src/xfinaudio/desktop/main_window.py` currently has a large `MainWindow.__init__` that performs these responsibilities in order:

1. Initializes workflow/session state and saved `selected_folder`.
2. Creates all public controls, labels, tables, combos, and inputs.
3. Sets initial labels, headers, enabled states, selection modes, wrapping, sizing, visibility, and placeholders.
4. Connects button/filter/table signals.
5. Applies visual styling.
6. Builds command bar, five workflow pages, west-positioned tabs, root layout, compact Mac layout, and central widget.

Existing tests in `tests/test_main_window.py` already characterize construction, labels, disabled actions, restored settings, visual styling, compact sizing, hidden initial sections, tab contract, table headers, wrapper methods, filtering, sorting, recommendation display, review/export behavior, and Prep Copilot controls.

## Design decisions

- **Private methods on `MainWindow`:** preserves Qt parent/ownership behavior and public widget attributes without broad data carrier classes.
- **Constructor remains the public contract:** callers continue to import and construct `MainWindow` from `xfinaudio.desktop.main_window`.
- **Move code, do not rewrite behavior:** implementation should primarily relocate existing constructor statements into helpers, avoiding copy/text/style changes.
- **One first slice under 400 changed lines:** use 4-5 helper methods and one focused characterization test; avoid broad decomposition into page-specific classes.
- **Order-sensitive side effects stay ordered:** `_apply_visual_design()` remains after widget creation and signal wiring, before compact layout; `_apply_compact_mac_layout(...)` remains after tabs/root layout are assembled and before `setCentralWidget(...)`.

## Proposed method boundaries

### `MainWindow.__init__(...) -> None`

Orchestrator only:

1. `super().__init__()`
2. `self._initialize_window_state(scan_service, repository, settings, settings_repository)`
3. `self.setWindowTitle("XfinAudio")`
4. `self._build_widgets()`
5. `self._connect_widget_signals()`
6. `self._apply_visual_design()`
7. `container = self._build_central_widget()`
8. `self.setCentralWidget(container)`

### `_initialize_window_state(...) -> None`

Moves the current non-widget initialization block unchanged:

- `workflow_service`, `settings`, `settings_repository`
- `selected_folder` initialization and final assignment from `self.settings.library.last_scan_folder`
- scanned/recommendation/readiness/Prep Copilot state
- worker references and cancellation token
- Serato export history, table sort order map, active search query, pre-scan record map

Important: do **not** call `set_selected_folder()` during construction; preserve direct assignment so saved-library state is not cleared.

### `_build_widgets() -> None`

Creates all constructor-owned public widget attributes and intrinsic widget state currently assigned before signal wiring, including:

- scan controls and labels
- decision/guidance labels
- safe export controls
- library filters, export button, and `tracks_table`
- strategy/recommendation controls
- Prep Copilot controls and table
- review/readiness/transition tables and labels
- Serato export history table, initially hidden
- label word-wrap, max-width, and max-height setup

The method must keep the same public attribute names on `self`.

### `_connect_widget_signals() -> None`

Moves signal wiring unchanged:

- button click handlers and existing export lambdas
- text/filter change handlers
- `tracks_table.itemSelectionChanged` refresh handler
- `prep_copilot_table.itemDoubleClicked` handler
- `_connect_table_sorting(...)` loop for all six tables

No signal should be intentionally added, removed, retargeted, or reordered relative to dependent widget creation.

### `_build_central_widget() -> QWidget`

Builds local layouts/pages/tabs and returns the central container:

- command controls row
- library status/filter controls
- recommendation controls
- Prep Copilot controls
- Library, Build Playlist, Review Mix, Export to Serato, Metadata Worklist pages
- `self.workflow_tabs` with west tab position and existing tab names/order
- root vertical layout with controls, tabs, and status label
- call `_apply_compact_mac_layout(layout, controls, recommendation_controls, library_status_controls, library_filter_controls, prep_copilot_controls)` before returning container

This helper may use local layout variables instead of storing page objects publicly, matching current behavior.

## Files to change

- `src/xfinaudio/desktop/main_window.py`
  - Extract constructor code into the private methods above.
  - Do not change `with_defaults`, worker methods, scan/recommend/export methods, table-populator wrappers, or app startup code.
- `tests/test_main_window.py`
  - Add one small offscreen characterization test before the refactor implementation in strict TDD.
  - Prefer reusable local helpers for table headers if already present.
- `openspec/changes/slim-main-window-panel-builders/design.md`
  - This design artifact.

Files explicitly not changed in this slice:

- `src/xfinaudio/desktop/app.py`
- `src/xfinaudio/desktop/table_populators.py`
- worker modules and workflow/service behavior

## Test plan

Strict TDD command: `uv run pytest -q`.

First add a failing or protective characterization test in `tests/test_main_window.py`, e.g. `test_main_window_constructor_exposes_initial_panel_contract`, that constructs `MainWindow` offscreen and verifies:

- Public table headers:
  - `tracks_table`: `Title`, `Artist`, `BPM`, `Key`, `Energy`, `Missing`, `Genre`, `Tags/Subgenre`, `Status`, `Path`
  - `recommendation_table`: current 11 recommendation headers
  - `prep_copilot_table`: `Variant`, `Readiness`, `Tracks`, `Warnings`
  - `transition_review_table`: `_TRANSITION_REVIEW_HEADERS` values by text
  - `serato_export_history_table`: current 6 export history headers
  - `dj_readiness_table`: `Check`, `Status`, `Detail`
- Workflow tabs: names/order and west tab position.
- Initial state: scan/recommend/cancel/export/prep-apply buttons disabled; Serato history/recommendation/readiness/Prep Copilot sections hidden as currently characterized; empty guidance labels unchanged.

Then perform the extraction and run:

- `uv run pytest -q`
- `uv run ruff check .`
- `uv run ruff format --check .`

## Data flow and contracts

Construction data flow remains unchanged:

1. Caller passes `scan_service`, `repository`, optional `settings`, optional `settings_repository`.
2. `_initialize_window_state` stores these dependencies and initializes runtime state.
3. `_build_widgets` creates public widgets on `self`.
4. `_connect_widget_signals` wires widgets to existing `MainWindow` slots.
5. `_build_central_widget` assembles existing pages/tabs and applies compact layout side effects.
6. Existing scan, filter, recommendation, Prep Copilot, review, export, and metadata methods operate on the same `self` attributes as before.

Public compatibility contract:

- `MainWindow` import path and constructor signature remain unchanged.
- Existing widget attributes remain public and usable.
- Existing wrapper methods remain callable.
- No new public panel-builder API is required or exposed.

## Rollout

This is an internal refactor with no migration or staged runtime rollout. Land as one small PR/slice after tests and lint pass. Keep the diff reviewable by avoiding broad formatting, copy edits, or unrelated cleanup.

## Rollback

Rollback is a clean git revert of the constructor extraction and the added characterization test. Since no schema, settings format, app entrypoint, worker behavior, or table-populator behavior changes are introduced, no data migration or operational rollback is required.

## Risks and mitigations

- **Lost public attribute:** characterization test checks key widget attributes and headers; implementation assigns widgets on `self`.
- **Changed signal behavior:** keep signal block unchanged in `_connect_widget_signals`; validate with existing interaction tests.
- **Changed construction order:** constructor orchestrator preserves styling and compact layout order.
- **Saved folder regression:** `_initialize_window_state` preserves direct `selected_folder` assignment from settings.
- **Changed UX/copy/layout:** no intentional text/layout changes; existing visual/tab/hidden-state tests continue to guard behavior.
- **Diff exceeds budget:** limit first slice to constructor private helpers plus one focused test.
