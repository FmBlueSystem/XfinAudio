# Proposal: slim-main-window-panel-builders

## Intent

Refactor `xfinaudio.desktop.main_window.MainWindow.__init__` into small private builder methods while preserving the existing desktop behavior and public compatibility contract. This is an approved continuation refactor, not a product feature.

The first implementation slice should make the constructor easier to understand and review without changing the `MainWindow` public API, widget attributes, signal wiring, labels, table headers, initial state, tab layout, visual styling, compact layout behavior, or the `xfinaudio.desktop.app:main` entrypoint.

## Proposal question round

Interactive SDD normally offers a short proposal question round before finalizing. Because this change is already framed as an approved behavior-preserving refactor with explicit constraints, this proposal proceeds with the following assumptions for user review:

1. The business objective is maintainability and reviewability of the desktop coordinator, not any user-visible workflow change.
2. The affected users are developers and reviewers working on `MainWindow`; desktop users should observe no difference.
3. The first slice should prefer private methods on `MainWindow` over a separate helper/factory module to minimize Qt ownership and public attribute risk.
4. The changed-line budget is a hard boundary for the first slice; broader decomposition should be deferred.
5. No copy, layout, workflow, entrypoint, persistence, scanning, recommendation, export, or metadata behavior should be intentionally changed.

If any of these assumptions are wrong, correct them before the design/tasks/apply phases.

## Scope

### In scope for the first slice

- Add or adjust a small offscreen Qt characterization test that snapshots constructor-created public widgets and important initial states.
- Extract constructor responsibilities into private `MainWindow` methods, such as:
  - `_initialize_window_state(...)`
  - `_build_widgets()` or narrowly grouped widget builders
  - `_connect_widget_signals()`
  - `_build_main_layout()` / `_build_central_widget()`
- Keep all existing public widget attributes assigned on `self` with the same names.
- Preserve current construction ordering, especially around `_apply_visual_design()` and `_apply_compact_mac_layout(...)`.
- Keep the first apply slice under the 400 changed-line review budget.

### Out of scope / deferred

- No product feature, UX, copy, layout, visual, or workflow changes.
- No public `MainWindow` API changes.
- No changes to the `xfinaudio.desktop.app:main` entrypoint.
- No separate panel-builder/helper module in the first slice unless later design work identifies a safe, reusable boundary.
- No table-populator changes, worker coordination changes, scan/recommend/export behavior changes, persistence changes, or broad state migration.
- No broad reformatting or opportunistic cleanup outside the constructor-builder extraction.

## Affected areas

- `src/xfinaudio/desktop/main_window.py`
  - Constructor orchestration and private helper organization only.
- `tests/test_main_window.py`
  - Small behavior-level characterization coverage for constructor-created widgets, table headers, tab labels/position, and initial enabled/hidden states.
- Existing OpenSpec requirement area: `openspec/specs/desktop-main-window/spec.md`
  - The refactor must continue to satisfy public entrypoint, public widget/wrapper compatibility, no-UX-change, and offscreen Qt characterization constraints.

## Behavior preservation requirements

The implementation MUST preserve:

- `MainWindow` import path and construction contract.
- Public widget attributes on `MainWindow`.
- Existing labels, guidance text, table headers, tab names, and tab position.
- Initial enabled/disabled states and hidden/visible states.
- Signal wiring behavior and ordering-sensitive connections.
- Existing table sorting/filtering behavior and wrapper methods.
- `_apply_visual_design()` and compact Mac layout side effects.
- `selected_folder` effective initialization from saved settings without invoking behavior that clears persisted library state during construction.

## Risks

- Moving code can accidentally change construction order, causing style, compact layout, hidden table, or enabled-state regressions.
- Signal wiring may be dropped or connected after dependent state changes.
- Public widgets may accidentally become locals instead of `self` attributes.
- A helper-module extraction could complicate Qt parent ownership and review scope; keep the first slice private to `MainWindow`.
- Broad cleanup could exceed the review budget and obscure behavior-preservation review.

## Rollback

Rollback is straightforward: revert the constructor extraction and its characterization test changes. Because the slice is behavior-preserving and should avoid schema, persistence, packaging, or entrypoint changes, no data migration or operational rollback is required.

## Success criteria

- `MainWindow` constructs successfully in offscreen Qt tests.
- Existing tests continue to pass without user-visible behavior changes.
- New/updated characterization coverage verifies key constructor-created widget attributes, headers, tab contract, and initial states.
- `xfinaudio.desktop.app:main` remains unchanged.
- First slice stays under 400 changed lines.
- Validation commands pass:
  - `uv run pytest -q`
  - `uv run ruff check .`
  - `uv run ruff format --check .`
