# Tasks: MainWindow Slice 3 Cleanup

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~145 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

## Phase 1: Lint Fixes

- [ ] 1.1 `src/xfinaudio/desktop/i18n.py` — Remove unused `import locale` (F401)
- [ ] 1.2 `src/xfinaudio/desktop/screens/build_screen.py:193` — Split E501 ternary into variable + `setText`
- [ ] 1.3 `src/xfinaudio/desktop/screens/review_screen.py:45` — Wrap E501 tooltip string with implicit concat under 120 cols
- [ ] 1.4 `src/xfinaudio/desktop/screens/review_screen.py:175` — Remove unused `header = table.horizontalHeader()` (F841)
- [ ] 1.5 `src/xfinaudio/desktop/screens/review_screen.py:246` — Add `strict=True` to `enumerate(zip(...))` (B905)
- [ ] 1.6 `src/xfinaudio/desktop/table_populators.py:162,164` — Break E501 `tips.append(...translate(...))` lines
- [ ] 1.7 `src/xfinaudio/library/track_repository.py:128-131` — Replace try/except-pass with `contextlib.suppress` + add import (SIM105)
- [ ] 1.8 Verify: `uv run ruff check src/ tests/` exits zero

## Phase 2: ExportHost Protocol

- [ ] 2.1 Audit every `self._host.X` access in `src/xfinaudio/desktop/export_coordinator.py` to capture full surface
- [ ] 2.2 Define `ExportHost(Protocol)` inline in `export_coordinator.py` with the 8 attributes, 1 writable attr, and 7 methods from design
- [ ] 2.3 Update `ExportCoordinator.__init__` signature: `host: ExportHost` instead of `host: "MainWindow"`
- [ ] 2.4 Remove the `TYPE_CHECKING` import of `MainWindow` from `export_coordinator.py`
- [ ] 2.5 Verify: `uv run pytest tests/ -q --tb=short` passes

## Phase 3: MenuBuilder Extraction

- [x] 3.1 Create `src/xfinaudio/desktop/menu_builder.py` with `MenuBuilder.__init__(host)` + `build(menu_bar)` + `show_about_dialog()` containing moved bodies from `_build_menu` (`:204-230`) and `_show_about_dialog` (`:232-265`)
- [x] 3.2 In `main_window.py:154`, add `self._menu_builder = MenuBuilder(self); self._menu_builder.build(self.menuBar())`
- [x] 3.3 Drop `_build_menu` and `_show_about_dialog` method bodies from `MainWindow`; no external callers (grep confirmed zero test/code refs) so no thin delegate kept
- [x] 3.4 Verify: `uv run pytest tests/ -q --tb=short` passes

## Phase 4: SettingsController Extraction

- [ ] 4.1 Create `src/xfinaudio/desktop/settings_controller.py` with `SettingsController.__init__(host)` + `open_dialog()` + `apply(new_settings)` containing moved bodies from `_open_settings_dialog` (`:1030-1036`) and `_apply_settings` (`:1038-1051`)
- [ ] 4.2 In `main_window.py`, add `self._settings_controller = SettingsController(self)` init; keep `_open_settings_dialog` → `self._settings_controller.open_dialog()` delegate and `_apply_settings` → `self._settings_controller.apply(...)` delegate (signal connections at `:696, :1035` depend on these names)
- [ ] 4.3 Verify: `uv run pytest tests/ -q --tb=short` passes

## Phase 5: Final Verification

- [ ] 5.1 `uv run ruff check src/ tests/` — zero errors
- [ ] 5.2 `uv run ruff format --check .` — passes
- [ ] 5.3 `uv run pytest -q` — zero failures
- [ ] 5.4 Confirm `MainWindow` line count decreased by ≥60 lines
