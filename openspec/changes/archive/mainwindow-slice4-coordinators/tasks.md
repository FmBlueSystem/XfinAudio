# Tasks: MainWindow Slice 4 — ScanCoordinator & RecommendationCoordinator

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~380 (add + del) |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | Single PR (two independent files) |
| Delivery strategy | ask-on-risk |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: single-pr
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | ScanCoordinator + ScanHost Protocol | PR 1 | Independent from unit 2; tests pass via delegation |
| 2 | RecommendationCoordinator + RecommendationHost Protocol | PR 1 | Independent from unit 1; tests pass via delegation |
| 3 | MainWindow wiring (imports, construction, signal rewire) | PR 1 | Depends on units 1 & 2 being present; no behavior change |

## Phase 1: ScanCoordinator Extraction

- [ ] 1.1 Create `src/xfinaudio/desktop/scan_coordinator.py` with `ScanHost(Protocol)` declaring `selected_folder`, `scanned_records`, `current_scan_cancellation_token`, `_pre_scan_records_by_path`, `_state`, `scan_button`, `recommend_button`, `cancel_scan_button`, `scan_progress_label`, `status_label`, `library_guidance_label`, `recommendation_guidance_label`, `tr`, `_sync_state`, `show_tracks`, `_clear_scan_dependent_state`, `_refresh_idle_action_state`
- [ ] 1.2 Implement `ScanCoordinator.__init__(self, host: ScanHost)` and methods: `scan_selected_folder`, `cancel`, `on_progress` (Slot), `on_completed` (Slot), `on_failed` (Slot), plus private `_begin_scan_state`, `_end_scan_state`, `_start_scan_worker`, `_show_scan_completion_status` — all moved verbatim from `MainWindow`
- [ ] 1.3 Update `main_window.py`: add `from xfinaudio.desktop.scan_coordinator import ScanCoordinator`; construct `self._scan_coordinator = ScanCoordinator(host=self)` in `_initialize_window_state`; replace `scan_selected_folder` and `cancel_scan` with 1-line delegations; remove moved private methods
- [ ] 1.4 Rewire `scan_progress_updated`, `scan_completed`, `scan_failed` signals in `_connect_widget_signals` to `self._scan_coordinator.on_progress`, `on_completed`, `on_failed`

## Phase 2: RecommendationCoordinator Extraction

- [ ] 2.1 Create `src/xfinaudio/desktop/recommendation_coordinator.py` with `RecommendationHost(Protocol)` declaring `scanned_records`, `workflow_service`, `_is_recommending`, `_state`, `recommend_button`, `scan_button`, `strategy_combo`, `recommendation_table`, `status_label`, `recommendation_guidance_label`, `last_recommendation`, `last_playlist_explanation`, `last_quality_report`, `tr`, `_sync_state`, `clear_recommendation_review`, `show_recommendation`, `show_transition_review`, `review_summary_label`, `export_guidance_label`, `_selected_track_controls`, `_desktop_recommendation_records`, `_set_recommendation_sections_expanded`, `_set_applied_copilot_variant`, `_show_dj_readiness`, `_refresh_idle_action_state`
- [ ] 2.2 Implement `RecommendationCoordinator.__init__(self, host: RecommendationHost)` and methods: `recommend`, `on_recommend_requested`, `on_completed` (Slot), `on_failed` (Slot), plus private `_begin_recommendation_state`, `_end_recommendation_state`, `_start_recommendation_worker` — all moved verbatim from `MainWindow`
- [ ] 2.3 Update `main_window.py`: add `from xfinaudio.desktop.recommendation_coordinator import RecommendationCoordinator`; construct `self._recommendation_coordinator = RecommendationCoordinator(host=self)` in `_initialize_window_state`; replace `recommend_playlist` and `_on_recommend_requested` with 1-line delegations; remove moved private methods
- [ ] 2.4 Rewire `recommendation_completed`, `recommendation_failed` signals in `_connect_widget_signals` to `self._recommendation_coordinator.on_completed`, `on_failed`

## Phase 3: Verification

- [ ] 3.1 Remove dead `_clear_scan_worker_refs` and `_clear_recommendation_worker_refs` stubs from `MainWindow` if signal defunct
- [ ] 3.2 Run `uv run pytest -q --tb=short` — all existing tests pass unmodified via delegates
- [ ] 3.3 Run `uv run ruff check .` — zero errors; verify coordinators type-check against Protocols, not `MainWindow`
- [ ] 3.4 Run `uv run ruff format --check .` — zero formatting issues
- [ ] 3.5 Confirm `MainWindow` line count decreased by 100+ (50 per coordinator per spec)
