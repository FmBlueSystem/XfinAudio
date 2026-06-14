# Apply Progress: mainwindow-slice3-cleanup

## Status

All phases complete. Commit delivered as part of the consolidated XfinAudio refactor commit.

## Completed Tasks

### Phase 1: Lint Fixes

- [x] 1.1 `src/xfinaudio/desktop/i18n.py` — Removed unused `import locale` (F401).
- [x] 1.2 `src/xfinaudio/desktop/screens/build_screen.py` — Split E501 ternary into variable + `setText`.
- [x] 1.3 `src/xfinaudio/desktop/screens/review_screen.py` — Wrapped E501 tooltip string.
- [x] 1.4 `src/xfinaudio/desktop/screens/review_screen.py` — Removed unused `header = table.horizontalHeader()` (F841).
- [x] 1.5 `src/xfinaudio/desktop/screens/review_screen.py` — Added `strict=True` to `enumerate(zip(...))` (B905).
- [x] 1.6 `src/xfinaudio/desktop/table_populators.py` — Broke E501 `tips.append(...translate(...))` lines.
- [x] 1.7 `src/xfinaudio/library/track_repository.py` — Replaced try/except-pass with `contextlib.suppress` (SIM105).
- [x] 1.8 Verified `uv run ruff check src/ tests/` exits zero.

### Phase 2: ExportHost Protocol

- [x] 2.1 Audited every `self._host.X` access in `src/xfinaudio/desktop/export_coordinator.py`.
- [x] 2.2 Defined `ExportHost(Protocol)` inline in `export_coordinator.py`.
- [x] 2.3 Updated `ExportCoordinator.__init__` signature: `host: ExportHost`.
- [x] 2.4 Removed the `TYPE_CHECKING` import of `MainWindow` from `export_coordinator.py`.
- [x] 2.5 Verified `uv run pytest tests/ -q --tb=short` passes.

### Phase 3: MenuBuilder Extraction

- [x] 3.1 Created `src/xfinaudio/desktop/menu_builder.py` with `MenuBuilder.__init__(host)`, `build(menu_bar)` and `show_about_dialog()`.
- [x] 3.2 Wired `MenuBuilder` into `MainWindow` initialization.
- [x] 3.3 Removed `_build_menu` and `_show_about_dialog` method bodies from `MainWindow`.
- [x] 3.4 Verified tests pass.

### Phase 4: SettingsController Extraction

- [x] 4.1 Created `src/xfinaudio/desktop/settings_controller.py` with `SettingsController.__init__(host)`, `open_dialog()` and `apply(new_settings)`.
- [x] 4.2 Wired `SettingsController` into `MainWindow` initialization; preserved `_open_settings_dialog` and `_apply_settings` thin delegates.
- [x] 4.3 Verified tests pass.

### Phase 5: Final Verification

- [x] 5.1 `uv run ruff check src/ tests/` — zero errors.
- [x] 5.2 `uv run ruff format --check .` — passes.
- [x] 5.3 `uv run pytest -q` — zero failures.
- [x] 5.4 `MainWindow` line count decreased well beyond the 60-line target (from ~1661 to 1307 lines as part of the broader refactor).
