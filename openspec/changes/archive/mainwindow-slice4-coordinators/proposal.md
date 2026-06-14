# Proposal: MainWindow Slice 4 — ScanCoordinator & RecommendationCoordinator

## Intent

Continue decomposing the 1585-line `MainWindow` by extracting scan and recommendation orchestration into dedicated coordinator classes, following the pattern established by `ExportCoordinator` in prior slices. This removes ~170 lines of state-transition and signal-handling logic from `MainWindow`, leaving thin delegations and formal Protocol boundaries.

## Scope

### In Scope
1. **ScanCoordinator extraction** — Move scan orchestration (`scan_selected_folder`, `_begin_scan_state`, `_end_scan_state`, `_start_scan_worker`, `_finish_scan`, `_fail_scan`, `_show_scan_progress`, `_show_scan_completion_status`, `cancel_scan`) from `MainWindow` into `ScanCoordinator`. `MainWindow` keeps thin delegations (`scan_selected_folder`, `cancel_scan`).
2. **ScanHost Protocol** — Define `ScanHost(Protocol)` with only the attributes/methods `ScanCoordinator` needs (e.g., `selected_folder`, `scanned_records`, `scan_button`, `cancel_scan_button`, `scan_progress_label`, `status_label`, `recommendation_guidance_label`, `show_tracks`, `_sync_state`). Replace any `TYPE_CHECKING` import of `MainWindow` to break circular coupling.
3. **RecommendationCoordinator extraction** — Move recommendation orchestration (`recommend_playlist`, `_begin_recommendation_state`, `_end_recommendation_state`, `_start_recommendation_worker`, `_finish_recommendation`, `_fail_recommendation`, `_on_recommend_requested`) into `RecommendationCoordinator`. `MainWindow` keeps thin delegations.
4. **RecommendationHost Protocol** — Define `RecommendationHost(Protocol)` with only the attributes `RecommendationCoordinator` needs (e.g., `scanned_records`, `recommend_button`, `scan_button`, `status_label`, `strategy_combo`, `recommendation_table`, `show_recommendation`, `clear_recommendation_review`, `_sync_state`).

### Out of Scope
- Further `MainWindow` decomposition (audio player, table populators, prep-copilot logic).
- Product behavior changes or UI redesign.
- New features or spec-level requirement changes.

## Capabilities

### New Capabilities
None

### Modified Capabilities
- `desktop-main-window`: extract ScanCoordinator and RecommendationCoordinator; formalize ScanHost and RecommendationHost Protocols.

## Approach

Apply behavior-preserving extraction following the `ExportCoordinator` → `ExportHost` precedent from slice 3:
- Move scan state-machine logic into `xfinaudio/desktop/scan_coordinator.py`.
- Move recommendation state-machine logic into `xfinaudio/desktop/recommendation_coordinator.py`.
- Define `ScanHost` and `RecommendationHost` Protocols in their respective coordinator modules (or a shared protocols module) exposing the minimal subset of `MainWindow` surface each coordinator reads/writes.
- `MainWindow` instantiates the new coordinators and passes `self` as the host; coordinators connect to `ScanController`/`RecommendationController` signals internally.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/xfinaudio/desktop/main_window.py` | Modified | Remove scan/recommendation orchestration logic; add thin delegations. Reduce line count by ~120–150 lines. |
| `src/xfinaudio/desktop/scan_coordinator.py` | New | Scan state machine, signal handling, and UI updates. |
| `src/xfinaudio/desktop/recommendation_coordinator.py` | New | Recommendation state machine, signal handling, and UI updates. |
| `src/xfinaudio/desktop/scan_controller.py` | Modified | No structural change; may update import if Protocol is defined in shared module. |
| `src/xfinaudio/desktop/recommendation_controller.py` | Modified | No structural change; may update import if Protocol is defined in shared module. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Protocol misses an attribute coordinator needs | Low | Audit all `host.` accesses in coordinator before defining Protocol; run tests. |
| Signal connections break in tests | Low | Preserve existing `MainWindow` public methods as thin delegates; run full test suite. |
| Coordinator incorrectly manages controller lifecycle | Low | Controller instantiation stays in `MainWindow.__init__`; coordinator only wires signals and calls methods. |

## Rollback Plan

Revert the individual commits. Each item is isolated to specific files with no schema or data migrations, so `git revert` restores prior behavior immediately.

## Dependencies

None

## Success Criteria

- [ ] `MainWindow` line count is reduced by at least 100 lines after extractions.
- [ ] All existing `MainWindow` tests pass without modification via thin delegation.
- [ ] `ScanCoordinator` and `RecommendationCoordinator` type-check against their respective Host Protocols instead of `MainWindow`.
- [ ] `uv run pytest -q` passes with zero failures.
- [ ] `uv run ruff check .` reports zero errors.
- [ ] `uv run ruff format --check .` passes.
