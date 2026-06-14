# Design: MainWindow Slice 5 — Final Alias & Coordinator Cleanup

## Technical Approach

Behavior-preserving extraction following the `ExportCoordinator` → `ExportHost` precedent (`export_coordinator.py`): coordinators take `host=self`, read state/widgets via a structural `Protocol`, and call repository/audio/screen APIs. Three independent items: (1) delete 27 widget property aliases (`main_window.py` 455–566) and repoint all test access to canonical `_screen` paths; (2) extract `PlaylistCoordinator` (net-new wiring — playlist screen signals are currently UNWIRED); (3) extract `LiveAssistantCoordinator` (re-home existing wiring at 669–672 + `_on_live_load_next` at 1410–1418).

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Coordinator boundary | `host: <X>Host(Protocol)` in coordinator module | Matches `ExportHost`; decouples from concrete `MainWindow`, satisfies success criterion (type-check vs Protocol). |
| `tracks_table` handling | KEEP — it is a real `MainWindow` attr (line 587), NOT an alias | Out of alias scope; `integration_flow.py` 190/191/205/210 stay valid. |
| `visible_tracks_table` (line 456) | DELETE alias + DELETE its only test | `test_visual_integration.py:187` is a self-referential identity assert (`window.visible_tracks_table is window._library_screen.tracks_table`) — meaningless once the alias is gone. |
| Playlist wiring | Coordinator OWNS new signal connections | Signals exist on screens but are unconnected in `MainWindow`; coordinator is the wiring home, not `MainWindow.__init__`. |
| Live load-next pool logic | Move `_on_live_load_next` body into coordinator | Candidate recalculation reads `_records_by_path`/`scanned_records` — pure host reads, clean to relocate. |

## Item 1 — Alias Removal (delete `main_window.py` 455–566)

27 aliases. Replacement = the body each property already returns. `window.tracks_table` is NOT here (real attr — leave alone).

| Line | Alias | Replacement path | Test usages (test_main_window.py) |
|------|-------|------------------|----------------|
| 456 | `visible_tracks_table` | `_library_screen.tracks_table` | 0 here; **delete** test_visual_integration.py:187 |
| 461 | `folder_button` | `_library_screen.folder_button` | 2 (126,140) + integration_flow |
| 465 | `scan_button` | `_library_screen.scan_button` | 8 + integration_flow 157,178 |
| 469 | `cancel_scan_button` | `_library_screen.cancel_button` | 9 |
| 473 | `serato_export_button` | `_export_screen.export_button` | 2 (206) |
| 477 | `dj_readiness_export_button` | `_export_screen.export_readiness_button` | 1 (207) |
| 482 | `recommend_button` | `_build_screen.recommend_button` | 29 + integration_flow 158,211,237 |
| 486 | `strategy_combo` | `_build_screen.strategy_combo` | 9 + integration_flow 235 |
| 490 | `prep_copilot_button` | `_build_screen.copilot_button` | 3 |
| 494 | `prep_copilot_apply_button` | `_build_screen.apply_variant_button` | 1 |
| 498 | `prep_copilot_target_count_input` | `_build_screen.target_count_input` | 12 |
| 502 | `prep_copilot_genre_focus_input` | `_build_screen.genre_focus_input` | 8 |
| 507 | `serato_preview_button` | `_export_screen.preview_button` | 3 |
| 511 | `review_summary_label` | `_review_screen.review_summary_label` | 5 |
| 515 | `dj_readiness_label` | `_review_screen.dj_readiness_label` | 4 |
| 519 | `applied_copilot_variant_label` | `_build_screen.applied_copilot_variant_label` | 5 |
| 523 | `export_guidance_label` | `_export_screen.export_guidance_label` | 13 |
| 527 | `safe_export_folder_label` | `_export_screen.safe_export_folder_label` | 5 |
| 532 | `dj_readiness_table` | `_review_screen.readiness_table` | 11 |
| 536 | `transition_review_table` | `_review_screen.transition_table` | 18 |
| 540 | `serato_export_history_table` | `_export_screen.history_table` | 13 |
| 544 | `recommendation_table` | `_review_screen.recommendation_table` | 14 + integration_flow 250,252 |
| 548 | `prep_copilot_table` | `_build_screen.copilot_table` | 23 |
| 553 | `song_search_input` | `_library_screen.search_input` | 7 + integration_flow 204,207 |
| 557 | `metadata_status_filter_combo` | `_metadata_screen.status_combo` | 2 |
| 561 | `missing_metadata_filter_combo` | `_metadata_screen.missing_combo` | 2 |
| 565 | `metadata_status_export_button` | `_metadata_screen.export_button` | 1 |

**Internal MainWindow callers also need repointing**: `_apply_compact_mac_layout` (691–700), `_apply_compact_table_columns` (716–720), `_apply_visual_design` (729–747), `_setup_connections` table loop (673–678). These use `self.<alias>` and break on deletion. `ExportCoordinator` reads `host.export_guidance_label`/`host.serato_export_history_table` — repoint to `host._export_screen.export_guidance_label`/`.history_table` and drop those two from `ExportHost`.

## Item 2 — PlaylistCoordinator (new `playlist_coordinator.py`)

Net-new wiring. Screen signals (currently unconnected): `MyPlaylistsScreen` (open/create/rename/duplicate/delete), `PlaylistEditor` (track_removed, tracks_reordered, export_requested, save_requested). `PlaylistRepository` API: `create`, `list_summaries`, `get_by_id`, `update_name`, `update_tracks`, `duplicate`, `delete`.

**Host accesses** → Protocol members: `_playlist_repository`, `_playlists_screen`, `_playlist_editor`, `workflow_tabs`, `_sync_state()`, `_records_by_path` (resolve track paths→records for editor), `tr()`.

```python
class PlaylistHost(Protocol):
    _playlist_repository: PlaylistRepository
    _playlists_screen: Any
    _playlist_editor: Any
    workflow_tabs: Any
    _records_by_path: dict[str, TrackRecord]
    def tr(self, text: str) -> str: ...
    def _sync_state(self) -> None: ...

class PlaylistCoordinator:
    def __init__(self, host: PlaylistHost) -> None:
        self._host = host
    def connect_signals(self) -> None: ...   # wire all list+editor signals
    def open_playlist(self, playlist_id: int) -> None: ...
    def create_playlist(self) -> None: ...
    def rename_playlist(self, playlist_id: int, name: str) -> None: ...
    def duplicate_playlist(self, playlist_id: int) -> None: ...
    def delete_playlist(self, playlist_id: int) -> None: ...
    def save_playlist(self, playlist_id: int, track_paths: list[str]) -> None: ...
    def export_playlist(self, playlist_id: int) -> None: ...
    def remove_track(self, path: str) -> None: ...
    def refresh_list(self) -> None: ...      # repopulate MyPlaylistsScreen summaries
```

## Item 3 — LiveAssistantCoordinator (new `live_assistant_coordinator.py`)

Re-home existing wiring (`main_window.py` 669–672) + move `_on_live_load_next` (1410–1418).

**Host accesses** → Protocol members: `_live_assistant_screen`, `_audio_player`, `workflow_tabs`, `_records_by_path` (line 1412), `scanned_records` (line 1417), plus `_on_preview_play_requested` for preview (or call `_audio_player.stop/load` directly — prefer host method to avoid duplicating preview logic).

```python
class LiveAssistantHost(Protocol):
    _live_assistant_screen: Any
    _audio_player: Any
    workflow_tabs: Any
    _records_by_path: dict[str, TrackRecord]
    scanned_records: list[TrackRecord]
    def _on_preview_play_requested(self, path: str) -> None: ...

class LiveAssistantCoordinator:
    def __init__(self, host: LiveAssistantHost) -> None:
        self._host = host
    def connect_signals(self) -> None:
        # exit→tab 0, preview→host._on_preview_play_requested, load_next→load_next
        ...
    def load_next(self, path: str) -> None:
        # moved _on_live_load_next: lookup record, set_current_track,
        # rebuild candidates (path != current, metadata_status=="complete")[:25],
        # set_candidates
        ...
```

`MainWindow` keeps thin `_on_live_load_next` delegating to coordinator (preserve any external callers/tests).

## Data Flow

    Screen signal ──→ Coordinator.handler ──→ Repository / AudioPlayer / Screen.set_*
                              │
                              └──→ host._sync_state()  (playlist mutations)

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `desktop/main_window.py` | Modify | Delete 455–566; repoint internal `self.<alias>` callers; instantiate two coordinators + call `connect_signals()`; thin live delegate. |
| `desktop/playlist_coordinator.py` | Create | `PlaylistHost` + `PlaylistCoordinator`; new signal wiring. |
| `desktop/live_assistant_coordinator.py` | Create | `LiveAssistantHost` + `LiveAssistantCoordinator`; moved load-next. |
| `desktop/export_coordinator.py` | Modify | Repoint `export_guidance_label`/`serato_export_history_table` to `_export_screen`; trim `ExportHost`. |
| `tests/test_main_window.py` | Modify | Replace ~210 alias accesses per table above. |
| `tests/integration_flow.py` | Modify | Repoint `scan_button`, `recommend_button`, `strategy_combo`, `song_search_input`, `recommendation_table`. |
| `tests/test_visual_integration.py` | Modify | Delete line 187 identity assert (alias gone). |

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | Coordinators | Fake host (SimpleNamespace) asserting repository/screen calls. |
| Integration | Alias migration | Existing `test_main_window.py` suite green after repointing. |
| E2E | Flows | `integration_flow.py` + `test_visual_integration.py` pass. |

Gates: `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check .`.

## Migration / Rollout

No data migration. Per-item commits; `git revert` restores prior behavior.

## Open Questions

- [ ] Does `_on_live_load_next` have external test callers requiring the `MainWindow` thin-delegate to survive? (search tests before removing.)
- [ ] Should playlist `export_requested` route through existing `ExportCoordinator`, or is it Serato-crate only? Confirm during apply.
