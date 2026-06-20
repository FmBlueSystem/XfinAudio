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

## TDD Cycle Evidence

| Slice | RED | GREEN | REFACTOR | VERIFY |
| --- | --- | --- | --- | --- |
| Recommend -> Save | `uv run pytest tests/test_application_vertical_playlist_flow.py -q` failed on missing `VerticalPlaylistFlow` import before the first facade implementation. | Added recommend/save facade and result. | Kept UI/controller code untouched. | Full gates passed during prior slice. |
| Scan -> Recommend | `uv run pytest tests/test_application_vertical_playlist_flow.py -q` failed with `AttributeError: 'VerticalPlaylistFlow' object has no attribute 'scan_and_recommend'`. | Added `scan_and_recommend()` and `VerticalScanRecommendationResult`. | Kept orchestration in application and UI worker ownership outside the facade. | Focused test, focused pyright, and ruff/format checks passed. |

## Current Scope Status

- Completed so far: recommendation -> saved playlist application boundary; scan -> recommendation application boundary.
- Still pending in this OpenSpec change: saved playlist -> export orchestration.

## Next Step

- Add the next RED test for saved-playlist-to-export orchestration without moving export policy into desktop/UI code.
