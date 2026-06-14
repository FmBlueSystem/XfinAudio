# Tasks: XfinAudio Live Assistant Mode

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 1200-1800 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 state+worker → PR 2 widgets → PR 3 MainWindow integration → PR 4 QA evidence |
| Delivery strategy | auto-chain |
| Chain strategy | feature-branch-chain |

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | LiveAssistantState + RecommendationWorker | PR 1 | Pure logic + background thread |
| 2 | LiveAssistantScreen widgets | PR 2 | NowPlaying, Suggestions, History |
| 3 | MainWindow integration | PR 3 | Tab, signals, keyboard shortcuts |
| 4 | QA evidence | PR 4 | Tests, verify report |

---

## Unit 1: State and Worker

### 1.1 RED: Add tests for LiveAssistantState

- [x] 1.1.1 Create `tests/test_live_assistant_state.py`
- [x] 1.1.2 Test state transitions: empty → ready → playing
- [x] 1.1.3 Test load_next updates history and current track
- [x] 1.1.4 Test alert generation (BPM guardrail, key clash, energy jump)
- [x] 1.1.5 Run and confirm failures

### 1.2 GREEN: Create LiveAssistantState

- [x] 1.2.1 Create `src/xfinaudio/desktop/live_assistant_state.py`
- [x] 1.2.2 Implement `SessionTrack`, `RiskAlert`, `LiveAssistantState`
- [x] 1.2.3 Implement `load_next`, `clear`, `generate_alerts` methods

### 1.3 RED: Add tests for RecommendationWorker

- [x] 1.3.1 Create `tests/test_recommendation_worker.py`
- [x] 1.3.2 Test worker runs recommendation in background
- [x] 1.3.3 Test cancellation token stops outdated requests
- [x] 1.3.4 Run and confirm failures

### 1.4 GREEN: Create RecommendationWorker

- [x] 1.4.1 Create `src/xfinaudio/desktop/recommendation_worker.py`
- [x] 1.4.2 Implement `RecommendationWorker` as `QRunnable`
- [x] 1.4.3 Use `QMetaObject.invokeMethod` to emit results to main thread

### 1.5 REFACTOR

- [x] 1.5.1 Ensure no Qt dependency in `live_assistant_state.py`
- [x] 1.5.2 Ensure thread-safe cancellation

---

## Unit 2: LiveAssistantScreen Widgets

### 2.1 RED: Add widget tests

- [x] 2.1.1 Create `tests/test_live_assistant_screen.py`
- [x] 2.1.2 Test screen constructs without error
- [x] 2.1.3 Test set_current_track updates NowPlayingWidget
- [x] 2.1.4 Test set_candidates populates SuggestionsWidget
- [x] 2.1.5 Test load_next emits signal
- [x] 2.1.6 Test preview button emits signal
- [x] 2.1.7 Run and confirm failures

### 2.2 GREEN: Create LiveAssistantScreen

- [x] 2.2.1 Create `src/xfinaudio/desktop/screens/live_assistant_screen.py`
- [x] 2.2.2 Build NowPlayingWidget with timer
- [x] 2.2.3 Build SuggestionsWidget with 3 CandidateRows
- [x] 2.2.4 Build SetHistoryWidget with QTableWidget
- [x] 2.2.5 Build EmptyStateWidget
- [x] 2.2.6 Connect keyboard shortcuts (Space, 1/2/3, Esc)

### 2.3 REFACTOR

- [x] 2.3.1 Ensure i18n with `self.tr()`
- [x] 2.3.2 Ensure parent widgets set for memory management

---

## Unit 3: MainWindow Integration

### 3.1 RED: Add integration tests

- [x] 3.1.1 Create `tests/test_main_window_live.py`
- [x] 3.1.2 Test Live Assistant tab exists
- [x] 3.1.3 Test keyboard shortcuts work
- [x] 3.1.4 Test audio preview coordination
- [x] 3.1.5 Run and confirm failures

### 3.2 GREEN: Wire into MainWindow

- [x] 3.2.1 Add LiveAssistantScreen to MainWindow tabs
- [x] 3.2.2 Connect LiveAssistantScreen signals to MainWindow handlers
- [x] 3.2.3 Wire audio preview through existing single-player coordinator
- [x] 3.2.4 Wire load_next to trigger background recommendation worker
- [x] 3.2.5 Update existing tab index tests

### 3.3 REFACTOR

- [x] 3.3.1 Ensure no memory leaks
- [x] 3.3.2 Ensure closeEvent stops any background workers

---

## Unit 4: QA Evidence

### 4.1 Automated gates

- [x] 4.1.1 Run `uv run pytest -q` → **711 passed, 0 failed**
- [x] 4.1.2 Run `uv run ruff check .` → New files clean
- [x] 4.1.3 Run `uv run ruff format --check .` → Clean

### 4.2 Verify report

- [x] 4.2.1 Create `verify-report.md`

---

## Files Changed

### New files
- `src/xfinaudio/desktop/live_assistant_state.py`
- `src/xfinaudio/desktop/recommendation_worker.py`
- `src/xfinaudio/desktop/screens/live_assistant_screen.py`
- `tests/test_live_assistant_state.py`
- `tests/test_recommendation_worker.py`
- `tests/test_live_assistant_screen.py`
- `tests/test_main_window_live.py`

### Modified files
- `src/xfinaudio/desktop/main_window.py`
- `src/xfinaudio/desktop/screens/__init__.py`
- `tests/test_main_window.py`
