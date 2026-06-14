# Design: MainWindow Slice 4 — ScanCoordinator & RecommendationCoordinator

## Technical Approach

Behavior-preserving extraction following the `ExportCoordinator`/`ExportHost` precedent (slice 3). Move the scan and recommendation state-machine + signal-handler logic out of `MainWindow` into two coordinators that access the window through structural `Protocol` hosts. `MainWindow` keeps thin public delegates and constructs/wires the coordinators in `__init__`. Controllers (`ScanController`, `RecommendationController`) are unchanged.

**Critical constraint**: `_sync_state` (lines 282–283) reads `current_scan_cancellation_token` and `_is_recommending`, and `_state.scan_progress_count` is read for status. These flags MUST stay on `MainWindow`/`_state` and be mutated through the host Protocol — coordinators cannot own them privately.

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Protocol location | Define `ScanHost`/`RecommendationHost` in their own coordinator modules | Matches `ExportHost` precedent (defined in `export_coordinator.py`); no shared module needed |
| State flags ownership | Stay on `MainWindow` (`current_scan_cancellation_token`, `_is_recommending`, `_state.*`); coordinator reads/writes via host | `_sync_state` already reads them; moving them breaks state rendering |
| Signal wiring | Coordinator exposes handler methods; `MainWindow._connect_controller_signals` connects controller→coordinator | Keeps controller lifetime in `MainWindow`; coordinator only wires behavior |
| Cross-cutting render calls | `_finish_recommendation` calls `_set_applied_copilot_variant`, `_show_dj_readiness`, `show_transition_review` → keep on host, call via Protocol | These belong to review/export concerns out of scope; expose as host methods |

## Scan Move Map

| Member (main_window.py:line) | Signature | Disposition |
|---|---|---|
| `scan_selected_folder` :1067 | `() -> None` | → coordinator; thin delegate stays |
| `_begin_scan_state` :1083 | `() -> None` | → coordinator |
| `_end_scan_state` :1093 | `() -> None` | → coordinator |
| `_start_scan_worker` :1100 | `(folder, token) -> None` | → coordinator |
| `_finish_scan` :1105 | `(result) -> None` `@Slot` | → coordinator handler |
| `_show_scan_completion_status` :1124 | `(records) -> None` | → coordinator |
| `_fail_scan` :1146 | `(error) -> None` `@Slot` | → coordinator handler |
| `_show_scan_progress` :1163 | `(progress) -> None` | → coordinator handler |
| `cancel_scan` :1173 | `() -> None` | → coordinator; thin delegate stays |

**Host members accessed** → `ScanHost`: `selected_folder`, `scanned_records`, `current_scan_cancellation_token`, `_pre_scan_records_by_path`, `_state`, `scan_button`, `recommend_button`, `cancel_scan_button`, `scan_progress_label`, `status_label`, `library_guidance_label`, `recommendation_guidance_label`, `tr`, `_sync_state`, `show_tracks`, `_clear_scan_dependent_state`, `_refresh_idle_action_state`.

## Recommendation Move Map

| Member (main_window.py:line) | Signature | Disposition |
|---|---|---|
| `recommend_playlist` :1280 | `() -> None` | → coordinator; thin delegate stays |
| `_begin_recommendation_state` :1363 | `(candidate_count) -> None` | → coordinator |
| `_end_recommendation_state` :1373 | `() -> None` | → coordinator |
| `_start_recommendation_worker` :1379 | `(records, strategy_name, controls=None) -> None` | → coordinator |
| `_finish_recommendation` :1387 | `(result) -> None` `@Slot` | → coordinator handler |
| `_fail_recommendation` :1417 | `(error) -> None` `@Slot` | → coordinator handler |
| `_on_recommend_requested` :1497 | `(strategy_name, paths) -> None` | → coordinator; thin delegate stays (BuildScreen adapter) |

**Host members accessed** → `RecommendationHost`: `scanned_records`, `workflow_service`, `_is_recommending`, `_state`, `recommend_button`, `scan_button`, `strategy_combo`, `recommendation_table`, `status_label`, `recommendation_guidance_label`, `last_recommendation`, `last_playlist_explanation`, `last_quality_report`, `tr`, `_sync_state`, `clear_recommendation_review`, `show_recommendation`, `show_transition_review`, `review_summary_label`, `export_guidance_label`, `_selected_track_controls`, `_desktop_recommendation_records`, `_set_recommendation_sections_expanded`, `_set_applied_copilot_variant`, `_show_dj_readiness`, `_refresh_idle_action_state`.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `desktop/scan_coordinator.py` | Create | `ScanHost(Protocol)` + `ScanCoordinator(host)` with public `scan_selected_folder`, `cancel`, and slot handlers `on_progress/on_completed/on_failed` |
| `desktop/recommendation_coordinator.py` | Create | `RecommendationHost(Protocol)` + `RecommendationCoordinator(host)` with public `recommend`, `on_recommend_requested`, slot handlers `on_completed/on_failed` |
| `desktop/main_window.py` | Modify | Remove ~13 methods; add coordinator construction in `_initialize_window_state`; rewire signals at :621–627; keep thin delegates |

## Interfaces / Contracts

```python
class ScanCoordinator:
    def __init__(self, host: ScanHost) -> None: ...
    def scan_selected_folder(self) -> None: ...
    def cancel(self) -> None: ...
    def on_progress(self, progress: ScanProgress) -> None: ...   # connect scan_progress_updated
    def on_completed(self, result: Any) -> None: ...             # connect scan_completed
    def on_failed(self, error: object) -> None: ...              # connect scan_failed

class RecommendationCoordinator:
    def __init__(self, host: RecommendationHost) -> None: ...
    def recommend(self) -> None: ...
    def on_recommend_requested(self, strategy_name: str, paths: list[str]) -> None: ...
    def on_completed(self, result: Any) -> None: ...             # connect recommendation_completed
    def on_failed(self, error: object) -> None: ...              # connect recommendation_failed
```

`MainWindow` thin delegates: `scan_selected_folder`→`_scan_coordinator.scan_selected_folder()`, `cancel_scan`→`_scan_coordinator.cancel()`, `recommend_playlist`→`_recommendation_coordinator.recommend()`, `_on_recommend_requested`→delegate. `closeEvent` controller `.cancel()` calls unchanged.

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | Coordinator state transitions against a fake host | New tests; assert host widget/flag mutations |
| Integration | Scan/recommend flows end-to-end | Existing `MainWindow` tests pass unmodified via delegates |
| Static | Coordinators type-check vs Host Protocols, not `MainWindow` | `uv run ruff check .`, mypy if configured |

## Migration / Rollout

No migration. Pure refactor, revert by commit.

## Open Questions

- [ ] Confirm `current_scan_cancellation_token` is set inside `_begin_scan_state` (coordinator) but read by `_sync_state` (host) — assign via `host.current_scan_cancellation_token = ...` (writable Protocol attr). Verified feasible: it is a plain instance attr (line 220), not a property.
