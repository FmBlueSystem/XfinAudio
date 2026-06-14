# Apply Progress: mainwindow-slice4-coordinators

## Status

All phases complete. Commit delivered as part of the consolidated XfinAudio refactor commit.

## Completed Tasks

### Phase 1: ScanCoordinator Extraction

- [x] 1.1 Created `src/xfinaudio/desktop/scan_coordinator.py` with `ScanHost(Protocol)` declaring the minimal surface used by the coordinator.
- [x] 1.2 Implemented `ScanCoordinator.__init__(self, host: ScanHost)` and methods: `scan_selected_folder`, `begin_scan_state`, `cancel`, `on_progress` (Slot), `on_completed` (Slot), `on_failed` (Slot), plus private `_start_scan_worker` helpers — all moved verbatim from `MainWindow`.
- [x] 1.3 Updated `main_window.py`: imported `ScanCoordinator`; constructed `self._scan_coordinator = ScanCoordinator(host=self)`; replaced `scan_selected_folder` and `cancel_scan` with thin delegations; removed moved private methods.
- [x] 1.4 Rewired `scan_progress_updated`, `scan_completed`, `scan_failed` signals to `self._scan_coordinator.on_progress`, `on_completed`, `on_failed`.

### Phase 2: RecommendationCoordinator Extraction

- [x] 2.1 Created `src/xfinaudio/desktop/recommendation_coordinator.py` with `RecommendationHost(Protocol)` declaring the minimal surface used by the coordinator.
- [x] 2.2 Implemented `RecommendationCoordinator.__init__(self, host: RecommendationHost)` and methods: `recommend`, `on_recommend_requested`, `on_completed` (Slot), `on_failed` (Slot), plus private `_begin_recommendation_state`, `_end_recommendation_state`, `_start_recommendation_worker` — all moved verbatim from `MainWindow`.
- [x] 2.3 Updated `main_window.py`: imported `RecommendationCoordinator`; constructed `self._recommendation_coordinator = RecommendationCoordinator(host=self)`; replaced `recommend_playlist` and `_on_recommend_requested` with thin delegations; removed moved private methods.
- [x] 2.4 Rewired `recommendation_completed`, `recommendation_failed` signals to `self._recommendation_coordinator.on_completed`, `on_failed`.

### Phase 3: Verification

- [x] 3.1 Removed dead `_clear_scan_worker_refs` and `_clear_recommendation_worker_refs` stubs from `MainWindow` where signal wiring became defunct.
- [x] 3.2 Ran `uv run pytest -q --tb=short` — all existing tests pass unmodified via delegates.
- [x] 3.3 Ran `uv run ruff check .` — zero errors; coordinators type-check against their Protocols, not `MainWindow`.
- [x] 3.4 Ran `uv run ruff format --check .` — zero formatting issues.
- [x] 3.5 Confirmed `MainWindow` line count decreased well beyond the 100-line target (from ~1585 to 1307 lines as part of the broader refactor).
