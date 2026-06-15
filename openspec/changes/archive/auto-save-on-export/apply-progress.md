# Apply Progress: Auto-save Playlist on Export

## Completed

- Added `ExportCoordinator(on_export_success=...)` and call it after successful Serato crate + readiness sidecar export.
- Wired `MainWindow` to pass `PlaylistCoordinator.save_recommendation` as the success hook.
- Updated default recommendation names to timestamp format: `{strategy} - %Y%m%d-%H%M%S`.
- Confirmed preview flow does not call the success hook.

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 2. export triggers save_recommendation | `tests/test_export_coordinator.py` | Unit | ✅ 108 focused tests passed | ✅ Failed: unexpected `on_export_success` kwarg | ✅ 17 focused tests passed | ✅ Success path with readiness sidecars | ✅ Callable hook kept coordinator decoupled |
| 3. preview does NOT trigger save | `tests/test_export_coordinator.py` | Unit | ✅ 108 focused tests passed | ✅ Failed: unexpected `on_export_success` kwarg | ✅ 17 focused tests passed | ✅ Preview path asserts hook not called | ✅ No production preview changes needed |
| 4. timestamped default name | `tests/test_playlist_coordinator.py` | Unit | ✅ 108 focused tests passed | ✅ Failed: old date-only name | ✅ 17 focused tests passed | ✅ Explicit name test preserves override behavior | ✅ Existing helper reused |

## Verification

- `uv run pytest tests/test_export_coordinator.py tests/test_playlist_coordinator.py tests/test_main_window.py -q` — PASS, 110 passed.
- Full verification suite — PASS (see `verify-report.md`).

## Remaining

- Commit and PR.
