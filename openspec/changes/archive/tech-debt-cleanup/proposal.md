# Proposal: Technical Debt Cleanup

## Intent

Remove dead code, align drifting configuration defaults, backfill missing tests for behaviors introduced in the previous performance cycle, and begin decomposing the 1900-line `MainWindow` god object by extracting export coordination.

## Scope

### In Scope
1. **Remove dead method** `_populate_prep_copilot_table` from `MainWindow` (replaced by `BuildScreen.render` in prior cycle; underlying free function in `table_populators.py` remains untouched).
2. **Align `optimizer.exact_limit` default** in `AppSettings` from `20` to `15` to match `optimizer.py`.
3. **Add missing tests** for previous-cycle behaviors:
   - `score_transition` cache hit and session-scoped cache clear.
   - Optimizer exact/heuristic boundary at n=15 vs n=16.
   - Scan thread guard cancels previous run.
   - Search debounce fires once after 150ms on rapid keystrokes.
4. **Extract export coordination** from `MainWindow` into `ExportCoordinator` (first slice only; ~200 lines).

### Out of Scope
- Full `MainWindow` decomposition (only export slice).
- Changes to heuristic optimizer internals.
- New product features or UI redesign.
- Modifying the free `populate_prep_copilot_table` function or its tests.

## Capabilities

### New Capabilities
None

### Modified Capabilities
- `desktop-main-window`: remove dead `_populate_prep_copilot_table`; extract export coordination into `ExportCoordinator`; adjust public methods to delegate.

## Approach

Apply targeted, test-backed cleanup:
- Delete the orphaned `_populate_prep_copilot_table` method from `MainWindow`.
- Change `OptimizerSettings.exact_limit` default from `20` to `15` in `settings.py`.
- Add four test groups covering cache behavior, optimizer boundary, thread guards, and debounce timing.
- Move `preview_export`, `export_recommendation`, Serato-specific preview/export, metadata worklist export, export history recording/rendering, and `_selected_export_software` from `MainWindow` into an expanded `ExportCoordinator` class. `MainWindow` keeps thin delegation methods to preserve the existing public contract and test assertions.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/xfinaudio/desktop/main_window.py` | Modified | Remove dead method; delegate export calls to `ExportCoordinator`. |
| `src/xfinaudio/desktop/export_coordinator.py` | Modified | Absorb export logic previously in `MainWindow`. |
| `src/xfinaudio/config/settings.py` | Modified | Align `optimizer.exact_limit` default to `15`. |
| `tests/test_transition_scoring.py` | Modified | Add cache hit and cache-clear tests. |
| `tests/test_sequence_optimizer.py` | Modified | Add n=15 exact / n=16 heuristic boundary test. |
| `tests/test_main_window.py` | Modified | Add thread-guard cancel and debounce tests. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Export extraction breaks existing test assertions on status labels | Low | Preserve thin `MainWindow` delegation methods; run full `test_main_window.py` suite before and after. |
| Settings default change surprises persisted user configs | Low | Only the factory default changes; persisted values remain intact. |
| Debounce test is flaky in CI | Low | Use `QTimer` single-shot with deterministic Qt event processing in tests. |

## Rollback Plan

Revert the individual commits. Each item is isolated to specific files with no schema or data migrations, so `git revert` restores prior behavior immediately.

## Dependencies

None

## Success Criteria

- [ ] `_populate_prep_copilot_table` is removed from `MainWindow` and `uv run pytest -q` still passes.
- [ ] `AppSettings().optimizer.exact_limit == 15`.
- [ ] Cache tests verify identical track pairs return same `TransitionScore` object and new sessions start with empty cache.
- [ ] Optimizer boundary test verifies n=15 routes to exact solver and n=16 routes to heuristic.
- [ ] Thread guard test verifies starting a second scan cancels the first.
- [ ] Debounce test verifies rapid text changes result in exactly one filter application after 150ms.
- [ ] `MainWindow` export methods still pass all existing export assertions via `ExportCoordinator` delegation.
- [ ] `uv run pytest -q` passes with zero failures.
- [ ] `uv run ruff check .` and `uv run ruff format --check .` pass.
