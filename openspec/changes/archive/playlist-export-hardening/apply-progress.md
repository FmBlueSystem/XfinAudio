# Apply Progress: Playlist & Export Hardening

## Completed

- [x] F1 — ReviewScreen exposes "Save to My Playlists", MainWindow wires it through PlaylistCoordinator, and generated recommendations are persisted with default `{strategy} - {date}` names.
- [x] F2 — MyPlaylistsScreen rename uses QInputDialog and emits only accepted non-empty names.
- [x] F3 — readiness sidecar export creates parent directories and Serato export reports sidecar write failures without bubbling.
- [x] F4 — saved playlist export builds a temporary recommendation and delegates to the Serato export flow with the playlist name as crate name.
- [x] F5 — spectral color jumps aggregate deterministically into one summary warning.
- [x] F7 — Metadata Worklist renders an explicit empty state when no library has been scanned.

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| F1 Save generated playlist | `tests/test_screens.py`, `tests/test_playlist_coordinator.py`, `tests/test_main_window_playlists.py` | UI/unit/integration | ✅ 133/133 baseline | ✅ Failed before production code | ✅ Focused tests passed | ✅ disabled/enabled/signal/save flow | ✅ Ruff formatted |
| F2 Rename dialog | `tests/test_my_playlists_screen.py` | UI unit | ✅ 133/133 baseline | ✅ Failed before production code | ✅ Focused tests passed | ✅ accepted/non-empty and blank/cancel | ✅ Ruff formatted |
| F3 Export resilience | `tests/test_export_coordinator.py` | Unit | ✅ 133/133 baseline | ✅ Failed before production code | ✅ Focused tests passed | ✅ mkdir and OSError paths | ✅ Ruff formatted |
| F4 Real playlist export | `tests/test_playlist_coordinator.py` | Unit | ✅ 133/133 baseline | ✅ Failed before production code | ✅ Focused tests passed | ✅ load editor and export delegation | ✅ Ruff formatted |
| F5 Spectral aggregation | `tests/test_playlist_service.py` | Unit | ✅ 133/133 baseline | ✅ Failed before production code | ✅ Focused tests passed | ✅ aggregate and missing/same-color paths | ✅ Ruff formatted |
| F7 Worklist empty state | `tests/test_screens.py` | UI unit | ✅ 133/133 baseline | ✅ Failed before production code | ✅ Focused tests passed | ✅ empty-state visibility | ✅ Ruff formatted |

## Verification

- ✅ Focused required tests: 161 passed.
- ✅ Full pytest: 810 passed.
- ✅ Pyright: 0 errors.
- ✅ Coverage: 88.37% total, above 70% gate.
- ✅ Ruff check and format check passed.
- ✅ Release gate passed.
