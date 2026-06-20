# Apply Progress: Vertical flow construction foundation

## 2026-06-20

- Created the SDD planning artifacts for the first post-minimum construction objective.
- Added `VerticalPlaylistFlow`, an application-level facade that composes existing recommendation and saved-playlist services.
- Added a RED/GREEN application test proving the facade recommends and saves without desktop/PySide dependencies.
- Kept UI/controller code untouched for this first boundary slice; no visible behavior changed.
- Full local XfinAudio gates passed for the recommend/save slice.

## 2026-06-20 Scan -> Recommend Slice

- RED: added `test_vertical_playlist_flow_scans_then_recommends_without_desktop_worker_ownership` to prove the vertical facade requests `scan_folder()` first and then calls `recommend()` with the scanned records.
- GREEN: added `VerticalPlaylistFlow.scan_and_recommend()` and `VerticalScanRecommendationResult` to compose existing application workflow collaborators without desktop/PySide imports.
- Preserved Qt worker/UI ownership outside application code by passing plain progress/cancellation collaborators through to `scan_folder()`; no worker construction or UI import was added.
- Export remains pending; this slice does not write files, mutate audio, touch Serato DB V2, or change dependencies.

## 2026-06-20 Saved Playlist -> Export Slice

- RED: added `test_vertical_playlist_flow_exports_saved_playlist_with_playlist_name_as_export_name` to prove `VerticalPlaylistFlow` exports a saved playlist through an injected application exporter fake and passes the saved playlist name as the requested export/crate name.
- GREEN: added `SavedPlaylistApplicationExporter`, `SavedPlaylistExportBuilder`, `SavedPlaylistStore`, `VerticalSavedPlaylistExportResult`, and `VerticalPlaylistFlow.export_saved_playlist()`.
- The vertical flow now asks the saved-playlist service to build the export recommendation, returns `None` for a missing saved playlist, and delegates export execution to the injected application exporter.
- No desktop/PySide imports were added; no export formats, Serato writers, filesystem writes, audio mutation, DSP scope, or live Serato DB V2 writes were introduced.

## TDD Cycle Evidence

| Slice | RED | GREEN | REFACTOR | VERIFY |
| --- | --- | --- | --- | --- |
| Recommend -> Save | `uv run pytest tests/test_application_vertical_playlist_flow.py -q` failed on missing `VerticalPlaylistFlow` import before the first facade implementation. | Added recommend/save facade and result. | Kept UI/controller code untouched. | Full gates passed during prior slice. |
| Scan -> Recommend | `uv run pytest tests/test_application_vertical_playlist_flow.py -q` failed with `AttributeError: 'VerticalPlaylistFlow' object has no attribute 'scan_and_recommend'`. | Added `scan_and_recommend()` and `VerticalScanRecommendationResult`. | Kept orchestration in application and UI worker ownership outside the facade. | Focused test, focused pyright, and ruff/format checks passed. |
| Saved Playlist -> Export | `uv run pytest tests/test_application_vertical_playlist_flow.py -q` failed with `TypeError: VerticalPlaylistFlow.__init__() got an unexpected keyword argument 'saved_playlist_exporter'`. | Added the exporter Protocol, result type, and `export_saved_playlist()` method. | Kept export execution behind an injected application-level exporter and left export writers unchanged. | Focused test, touched-file pyright, ruff, format, and full XfinAudio gates passed on 2026-06-20. |

## Current Scope Status

- Completed functional scope: recommendation -> saved playlist application boundary; scan -> recommendation application boundary; saved playlist -> export application boundary.
- Still pending in this OpenSpec change: archive the verified change.

## Next Step

- Archive the OpenSpec change after confirming the final verification report remains current.
