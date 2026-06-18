# Tasks: Slice main_window final

Strict TDD applies. 848 tests is the contract.

## 1. Pre-flight
- [ ] `git status` clean.
- [ ] `uv run pytest -q` → 848 passed.

## 2. Move factory methods
- [x] Move `_initialize_library_controller` to `window_factory.py`.
- [x] Move `_replace_app_state` to `window_factory.py`.
- [x] Move `_initialize_app_controller` to `window_factory.py`.
- [x] Move `with_defaults` to `window_factory.py`.
- [x] Update `MainWindow.__init__` to call the factory functions.
- [x] `uv run pytest -q` → green.

## 3. Move settings apply
- [x] Move `_apply_settings` to `settings_controller.py`.
- [x] Update call sites.
- [x] `uv run pytest -q` → green.

## 4. Move prep copilot variant set
- [x] Move `_set_applied_copilot_variant` to `prep_copilot.py`.
- [x] Update call sites.
- [x] `uv run pytest -q` → green.

## 5. Move _on_* handlers
- [x] Move the 16 `_on_*` and 2 `_open_selected_*` / `_remove_selected_*` methods
  to `library_controller.py`.
- [x] Update signal connections in `_connect_screens` and per-screen
  `connect_signals` to call the controller methods.
- [x] `uv run pytest -q` → green.

## 6. Move _LAYOUT_METHODS dict
- [x] Create `layout.install_layout_methods(target_class)` in `layout.py`.
- [x] Move the dict and the `setattr` loop into it.
- [x] Call `install_layout_methods(MainWindow)` after the class definition.
- [x] `uv run pytest -q` → green.

## 7. Remove 1-line shim methods
- [x] Remove the 18 1-line shim methods.
- [x] Update every call site to call the controller directly.
- [x] `uv run pytest -q` → green.

## 8. Verify
- [x] `wc -l src/xfinaudio/desktop/main_window.py` is under 400.
- [x] `uv run pytest -q` → 848 passed.
- [x] `uv run ruff check .` → green.
- [x] `uv run pyright src tests` → green.
- [x] `uv run python scripts/source_package_hygiene_check.py` → green.

## 9. Commit and open PR
- [ ] Single work-unit commit.
- [ ] Push, open PR against main.
- [ ] Update state.yaml, write apply-progress.md.
