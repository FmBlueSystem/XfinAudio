# Design: Playlist & Export Hardening

## Decision question

How do we close the gaps found in the Fagan audit without introducing regressions?

## Alternatives considered (Arbor-style)

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. One big change with all 6 fixes | Atomic; one PR. | Mixes refactor, UX, safety; hard to review. | Rejected. |
| B. Group F1+F2+F3+F4+F5+F7 in one "hardening" change, F6 in a separate refactor | Coherent UX/safety scope; manageable line budget; easier rollback. | Two PRs instead of one. | **Selected.** |
| C. One fix per PR | Maximum reviewability. | Six PRs for small fixes is overhead. | Rejected. |

## Architecture impact

- `ReviewScreen` gains a `save_to_playlists_requested` signal.
- `MainWindow` wires it to `PlaylistCoordinator.save_recommendation`.
- `PlaylistCoordinator.save_recommendation` calls `repository.create(name, track_paths)` with a default name.
- `MyPlaylistsScreen._on_rename_clicked` uses `QInputDialog.getText` and emits the real name.
- `PlaylistCoordinator.export_playlist` builds a temporary `PlaylistRecommendation` from the saved tracks and delegates to `ExportCoordinator.export_recommendation_to_serato`.
- `write_readiness_sidecars` (or `write_dj_readiness_report`) calls `base.mkdir(parents=True, exist_ok=True)`.
- `playlist_service._spectral_jump_warnings` aggregates runs of same-direction color shifts.
- `metadata_screen.render` shows an empty-state label in the worklist table when no records.

## Affected files

- `src/xfinaudio/desktop/screens/review_screen.py`
- `src/xfinaudio/desktop/main_window.py`
- `src/xfinaudio/desktop/playlist_coordinator.py`
- `src/xfinaudio/desktop/screens/my_playlists_screen.py`
- `src/xfinaudio/desktop/export_coordinator.py`
- `src/xfinaudio/quality/dj_readiness.py`
- `src/xfinaudio/recommendation/playlist_service.py`
- `src/xfinaudio/desktop/screens/metadata_screen.py`
- `tests/` (corresponding test files)

## Safety

- No audio mutation.
- No DSP scope expansion.
- No live Serato Database V2 writes.
- The export resilience fix is a pure safety improvement.
