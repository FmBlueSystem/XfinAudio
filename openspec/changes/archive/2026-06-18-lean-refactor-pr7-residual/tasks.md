# Tasks: Slice main_window residual

Strict TDD applies. This is a refactor with no behavioral surface; the test suite
(848 tests) is the contract. The "test" for each step is the existing regression
suite passing without modification of assertions.

## 1. Pre-flight

- [ ] `git status` clean.
- [ ] `uv run pytest -q` → 848 passed.
- [ ] `uv run ruff check .` → green.
- [ ] `uv run pyright src tests` → green.

## 2. Property accessors: add attributes to AppState

- [x] Read `app_state.py` to confirm the 15 names are already attributes.
- [x] If any are missing, add them.
- [x] `uv run pytest -q` → green.

## 3. Property accessors: add dunder methods to MainWindow

- [x] Add `__getattr__` and `__setattr__` to `MainWindow`.
- [x] Add `_APP_STATE_ATTRIBUTES` frozenset with the 15 names.
- [x] `uv run pytest -q` → green.

## 4. Property accessors: remove the 15 property accessors

- [x] Delete the 15 `@property` / `@<name>.setter` definitions.
- [x] `uv run pytest -q` → green.

## 5. Per-screen signal wiring

- [x] Read each screen file to find its existing signals.
- [x] Add `connect_signals(window)` to each of:
  - LibraryScreen, BuildScreen, ReviewScreen, ExportScreen, MetadataScreen,
    MyPlaylistsScreen, PlaylistEditor
  - LiveAssistantScreen already has `connect_signals`; update it.
- [x] Move the relevant signal connections from
  `MainWindow._connect_widget_signals` into the per-screen method.
- [x] Update `MainWindow.__init__` to iterate over screens and call
  each `connect_signals(self)`.
- [x] Remove `MainWindow._connect_widget_signals`.
- [x] `uv run pytest -q` → green.

## 6. Full build_layout + build_widgets move

- [x] Read the current bodies of `MainWindow._build_layout` and
  `MainWindow._build_widgets`.
- [x] Move them to `layout.py` as `build_main_window_layout(window)` and
  `build_main_widgets(window)`.
- [x] MainWindow's methods become one-line shims.
- [x] `uv run pytest -q` → green.

## 7. _initialize_window_state factory

- [x] Create `src/xfinaudio/desktop/window_factory.py` with
  `initialize_window_state(window, scan_service, repository, settings,
  settings_repository)`.
- [x] Move the body of `MainWindow._initialize_window_state` into the factory.
- [x] MainWindow's method becomes a one-line shim.
- [x] `uv run pytest -q` → green.

## 8. Verify

- [x] `git ls-files` confirms the new window_factory.py.
- [x] `wc -l src/xfinaudio/desktop/main_window.py` is under 700.
- [x] `uv run pytest -q` → 848 passed.
- [x] `uv run ruff check .` → green.
- [x] `uv run pyright src tests` → green.
- [x] `uv run python scripts/source_package_hygiene_check.py` → green.

## 9. Commit and open PR

- [x] Single work-unit commit: `refactor(desktop): extract signal wiring, layout, and state from main_window`.
- [x] Push: `git push -u origin refactor/slice-mainwindow-residual`.
- [x] Open PR against `main`.
- [x] Update `state.yaml` → state: verifying, apply: complete.
- [x] Write `apply-progress.md`.
