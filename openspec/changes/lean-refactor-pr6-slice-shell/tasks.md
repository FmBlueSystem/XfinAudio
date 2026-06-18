# Tasks: Slice main_window shell

Strict TDD applies. This is a refactor with no behavioral surface; the test suite
(848 tests) is the contract. The "test" for each step is the existing regression
suite passing without modification of assertions.

## 1. Pre-flight

- [ ] `git status` clean.
- [ ] `uv run pytest -q` → 848 passed.
- [ ] `uv run ruff check .` → green.
- [ ] `uv run pyright src tests` → green.

## 2. Extract AppController

- [x] Create `src/xfinaudio/desktop/app_controller.py` with `AppController`.
- [x] Update `main_window.py`:
  - Construct `self._app_controller` in `_initialize_window_state`.
  - Replace the 6 sync/render methods with one-line shims.
  - Update `_render_screens`, `_sync_state`, `_on_tab_changed`,
    `_update_tab_states`, `_render_tab`, `_refresh_state_fields` to delegate.
- [x] `uv run pytest -q` → green.

## 3. Extract LibraryController

- [x] Create `src/xfinaudio/desktop/library_controller.py` with
  `LibraryController`.
- [x] Update `main_window.py`:
  - Construct `self._library_controller` in `_initialize_window_state`.
  - Replace the 17 library methods with one-line shims.
  - Move the spectral worker setup and slot methods to the controller.
- [x] `uv run pytest -q` → green.

## 4. Extract SettingsController

- [x] Create `src/xfinaudio/desktop/settings_controller.py` with
  `SettingsController`.
- [x] Update `main_window.py`:
  - Construct `self._settings_controller` in `_initialize_window_state`.
  - Replace the 4 settings methods with one-line shims.
- [x] `uv run pytest -q` → green.

## 5. Extract DjReadinessController

- [x] Create `src/xfinaudio/desktop/dj_readiness_controller.py` with
  `DjReadinessController`.
- [x] Update `main_window.py`:
  - Construct `self._dj_readiness_controller` in `_initialize_window_state`.
  - Replace `_show_dj_readiness` and `_populate_dj_readiness_table` with
    one-line shims.
- [x] `uv run pytest -q` → green.

## 6. Verify

- [ ] `git ls-files` confirms the 4 new files exist.
- [ ] `wc -l src/xfinaudio/desktop/main_window.py` is under 600.
- [x] `uv run pytest -q` → 848 passed.
- [x] `uv run ruff check .` → green.
- [x] `uv run pyright src tests` → green.
- [x] `uv run python scripts/source_package_hygiene_check.py` → green.

## 7. Commit and open PR

- [ ] Single work-unit commit: `refactor(desktop): extract 4 controllers from main_window`.
- [ ] Push: `git push -u origin refactor/slice-mainwindow-shell`.
- [ ] Open PR against `main` (not the tracker — this is a post-chain PR).
- [ ] Update `state.yaml` → state: verifying, apply: complete.
- [ ] Write `apply-progress.md`.
- [ ] After PR 6 merges, branch off `main` for PR 7
  (`refactor/slice-mainwindow-residual`).
