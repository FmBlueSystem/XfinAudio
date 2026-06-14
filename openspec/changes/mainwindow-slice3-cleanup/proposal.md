# Proposal: MainWindow Slice 3 Cleanup

## Intent

Continue decomposing the 1661-line `MainWindow` by extracting menu and settings responsibilities, formalize the `ExportCoordinator` host boundary with a Protocol, and fix 7 pre-existing lint errors.

## Scope

### In Scope
1. **MenuBuilder extraction** — Move `_build_menu` and `_show_about_dialog` from `MainWindow` into a `MenuBuilder` class. `MainWindow` keeps thin delegation (`self._menu_builder.build(self.menuBar())`).
2. **SettingsController extraction** — Move `_open_settings_dialog` and `_apply_settings` into a `SettingsController`. `MainWindow` keeps thin delegation.
3. **ExportHost Protocol** — Define an `ExportHost` Protocol with only the attributes/methods `ExportCoordinator` actually accesses. Replace the `TYPE_CHECKING` import of `MainWindow` to break circular coupling and enable independent coordinator testing.
4. **Fix 7 pre-existing lint errors** — `i18n.py` (F401), `build_screen.py` (E501), `review_screen.py` (E501×2, F841, B905), `table_populators.py` (E501×2), `track_repository.py` (SIM105).

### Out of Scope
- Further `MainWindow` decomposition (audio player, scan/recommendation controllers, table populators).
- Product behavior changes or UI redesign.
- New features or spec-level requirement changes.

## Capabilities

### New Capabilities
None

### Modified Capabilities
- `desktop-main-window`: extract MenuBuilder and SettingsController; formalize ExportHost Protocol for ExportCoordinator.

## Approach

Apply behavior-preserving extraction:
- Move menu construction and about-dialog logic into `xfinaudio/desktop/menu_builder.py`.
- Move settings dialog handling into `xfinaudio/desktop/settings_controller.py`.
- Define `ExportHost` Protocol in `xfinaudio/desktop/export_coordinator.py` (or a shared protocols module) exposing the subset of `MainWindow` surface that `ExportCoordinator` reads/writes.
- Apply targeted ruff fixes to the 7 known errors without changing behavior.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/xfinaudio/desktop/main_window.py` | Modified | Remove menu/settings logic; add thin delegation. Reduce line count. |
| `src/xfinaudio/desktop/menu_builder.py` | New | Menu construction and About dialog. |
| `src/xfinaudio/desktop/settings_controller.py` | New | Settings dialog creation and application. |
| `src/xfinaudio/desktop/export_coordinator.py` | Modified | Replace `MainWindow` TYPE_CHECKING import with `ExportHost` Protocol. |
| `src/xfinaudio/desktop/i18n.py` | Modified | Remove unused `locale` import. |
| `src/xfinaudio/desktop/screens/build_screen.py` | Modified | Fix E501. |
| `src/xfinaudio/desktop/screens/review_screen.py` | Modified | Fix E501×2, F841, B905. |
| `src/xfinaudio/desktop/table_populators.py` | Modified | Fix E501×2. |
| `src/xfinaudio/library/track_repository.py` | Modified | Fix SIM105. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Menu/settings signal connections break in tests | Low | Preserve existing `MainWindow` public methods as thin delegates; run full test suite. |
| Protocol misses an attribute ExportCoordinator needs | Low | Audit all `host.` accesses in coordinator before defining Protocol; run tests. |
| Lint fixes touch adjacent logic accidentally | Low | Make minimal one-line fixes; review diff before commit. |

## Rollback Plan

Revert the individual commits. Each item is isolated to specific files with no schema or data migrations, so `git revert` restores prior behavior immediately.

## Dependencies

None

## Success Criteria

- [ ] `MainWindow` line count is reduced by at least 60 lines after MenuBuilder and SettingsController extractions.
- [ ] All existing `MainWindow` tests pass without modification via thin delegation.
- [ ] `ExportCoordinator` type-checks against `ExportHost` Protocol instead of `MainWindow`.
- [ ] `uv run pytest -q` passes with zero failures.
- [ ] `uv run ruff check .` reports zero errors.
- [ ] `uv run ruff format --check .` passes.
