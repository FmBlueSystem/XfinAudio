# Proposal: slim-main-window-widget-builders

## Intent

Continue the approved behavior-preserving refactor of `xfinaudio.desktop.main_window.MainWindow.__init__`. This slice (PR 2 in the archived panel-builder chain) extracts the constructor's widget creation and intrinsic widget configuration block into a private `MainWindow._build_widgets() -> None` method. It is a maintainability/reviewability refactor, not a product feature or UX change.

## Capabilities

This change modifies exactly one existing capability and adds no new public capability:

- `desktop-main-window`: continues to satisfy all existing requirements. Specifically, the slice exercises:
  - Public Desktop Entry Point Compatibility — `xfinaudio.desktop.app:main` and the `MainWindow` import/construction contract stay unchanged.
  - Public Widget and Wrapper Method Compatibility — public widget attributes, signals, and wrapper methods remain available and observably identical.
  - Constructor Builder Extraction Preservation — widget creation moves into a private builder while the constructed window stays externally indistinguishable; no new public panel-builder API.
  - Initial Desktop UI State Preservation — labels, headers, tab contract, visibility, enabled states, and guidance text are preserved.
  - No Product Feature or UX Change — no copy, layout, workflow, or visual change.
  - Offscreen Qt Characterization Coverage — existing offscreen tests continue to lock the constructor contract.

A focused delta spec tightens the existing `desktop-main-window` refactor guarantees for this slice; it does not introduce product behavior or public API changes.

## Scope

### In scope

- Add a private `MainWindow._build_widgets()` and move only the existing widget construction/configuration block into it: window title, all public widget attribute assignments, table header setup, table selection behavior/mode, initial enabled/visible states, and label word-wrap/size constraints.
- Call `_build_widgets()` after `_initialize_window_state(...)` and before `_connect_widget_signals()`, preserving ordering around `_apply_visual_design()`, layout assembly, and `_apply_compact_mac_layout(...)`.
- Optionally add one focused offscreen characterization assertion group for `tracks_table` / `prep_copilot_table` selection modes.

### Out of scope / deferred

- Central/page/tab layout assembly extraction (deferred to PR 3).
- Table-populator, worker, export, recommendation, scanning, metadata, or persistence behavior.
- `app.py` entrypoint changes and any new public panel-builder module.
- Broad reformatting or opportunistic cleanup.

## Affected areas

- `src/xfinaudio/desktop/main_window.py` — constructor organization only.
- `tests/test_main_window.py` — only if adding the optional selection-mode characterization.

## Risks

- `_build_widgets()` must run before `_connect_widget_signals()` and `_apply_visual_design()`, which assume every widget attribute exists.
- Keep `tracks_table.itemSelectionChanged` wiring in `_connect_widget_signals()`, not in `_build_widgets()`.
- Preserve initial hidden/enabled states (e.g. `serato_export_history_table`, recommendation/prep sections) set via existing compact/section side effects.

## Rollback

Revert the constructor extraction and any added test. No data, schema, or entrypoint migration is involved.

## Success criteria

- Offscreen Qt construction succeeds; existing tests pass unchanged.
- Slice stays under the 400 changed-line review budget.
- `uv run pytest -q`, `uv run ruff check .`, and `uv run ruff format --check .` pass.
