# Tasks: Slice main_window.py (partial)

Strict TDD applies. This is a refactor with no behavioral surface; the test suite
(848 tests after PR 4) is the contract. The "test" for each step is the existing
regression suite passing without modification of assertions.

## 1. Pre-flight

- [ ] `git status` clean.
- [ ] `uv run pytest -q` → 848 passed.
- [ ] `uv run ruff check .` → green.
- [ ] `uv run pyright src tests` → green.

## 2. Extract `responsive_sidebar_width` to `layout.py`

- [x] Create `src/xfinaudio/desktop/layout.py` with the function.
- [x] Update `main_window.py` import.
- [x] `uv run pytest tests/test_main_window.py -q` → green.

## 3. Extract `WorkflowStack` to `workflow_stack.py`

- [x] Create `src/xfinaudio/desktop/workflow_stack.py` with the class.
- [x] Update `main_window.py` import.
- [x] `uv run pytest tests/test_main_window.py -q` → green.

## 4. Move `SettingsPersistence` Protocol to `app_state.py`

- [x] Add the Protocol to `app_state.py`.
- [x] Update `main_window.py` import.
- [x] `uv run pytest tests/test_main_window.py -q` → green.

## 5. Extract undo toolbar to `undo_toolbar.py`

- [x] Create `src/xfinaudio/desktop/undo_toolbar.py` with `UndoToolbar`.
- [x] Construct in `_initialize_window_state`.
- [x] Replace `undo`, `redo`, `_refresh_undo_state` with shims.
- [x] `uv run pytest -q` → green.

## 6. Extract keyboard shortcuts to `shortcuts.py`

- [x] Create `src/xfinaudio/desktop/shortcuts.py` with `bind_main_window_shortcuts`.
- [x] Replace `_connect_keyboard_shortcuts` with a call to it.
- [x] `uv run pytest -q` → green.

## 7. Extract responsive resize to `responsive.py`

- [x] Create `src/xfinaudio/desktop/responsive.py` with `ResponsiveLayout`.
- [x] Wire in `_initialize_window_state`.
- [x] Replace `resizeEvent` and `_apply_responsive_layout` with delegations.
- [x] `uv run pytest -q` → green.

## 8. Extract visual design to `visual_design.py`

- [x] Create `src/xfinaudio/desktop/visual_design.py` with `apply_visual_design`.
- [x] Replace the three visual methods with one call.
- [x] `uv run pytest -q` → green.

## 9. Extract table sorting to `table_sorting.py`

- [x] Create `src/xfinaudio/desktop/table_sorting.py` with `connect_table_sorting`.
- [x] Replace `_connect_table_sorting` and `_sort_table_by_column` with a shim.
- [x] `uv run pytest -q` → green.

## 10. Extract prep copilot to `prep_copilot.py`

- [x] Create `src/xfinaudio/desktop/prep_copilot.py` with `PrepCopilotController`.
- [x] Wire in `_initialize_window_state`.
- [x] Replace the four prep-copilot methods with delegations.
- [x] `uv run pytest -q` → green.

## 11. Extract recommendation rendering to `recommendation_render.py`

- [x] Create `src/xfinaudio/desktop/recommendation_render.py` with the three
  render functions.
- [x] Replace `show_recommendation`, `clear_recommendation_review`,
  `show_transition_review` with delegations.
- [x] `uv run pytest -q` → green.

## 12. Extract export thin wrappers to `export_actions.py`

- [x] Create `src/xfinaudio/desktop/export_actions.py` with `ExportActions`.
- [x] Wire in `_initialize_window_state`.
- [x] Replace the 8 export methods with delegations.
- [x] `uv run pytest -q` → green.

## 13. Verify

- [x] `git ls-files` confirms the 10 new files exist.
- [x] `wc -l src/xfinaudio/desktop/main_window.py` is under 1100.
- [x] `uv run pytest -q` → 848 passed.
- [x] `uv run ruff check .` → green.
- [x] `uv run pyright src tests` → green.
- [x] `uv run python scripts/source_package_hygiene_check.py` → green.

## 14. Commit and merge

- [x] One work-unit commit: `refactor(desktop): slice main_window into 10 helper modules`.
- [x] Push the branch.
- [x] Open PR against `tracker/lean-refactor`.
- [x] Update state.yaml → state: verifying, apply: complete.
- [x] Write apply-progress.md.
- [x] After PR 5 merges, the `lean-refactor` chain is complete. The tracker can
  then be fast-forwarded to `main` (or merged via a single integration PR per
  repo policy).
- [x] Document the residual (`main_window` still ~1020 LOC; further slicing is
  a follow-up) in the PR body.
