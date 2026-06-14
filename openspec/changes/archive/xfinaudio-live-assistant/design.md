# Design: Live Assistant Mode

## Architecture

The Live Assistant is a new screen (`LiveAssistantScreen`) added to the main tab widget. It operates in two modes:
1. **Library mode**: Uses the full scanned library as candidate pool
2. **Playlist mode**: Uses a loaded saved playlist as candidate pool

### Component Diagram

```
MainWindow
├── LiveAssistantScreen (new tab)
│   ├── NowPlayingWidget
│   │   └── Displays current TrackRecord + session timer
│   ├── SuggestionsWidget
│   │   ├── CandidateRow (x3)
│   │   │   ├── Track info labels
│   │   │   ├── Preview button (▶/⏸)
│   │   │   ├── Load Next button
│   │   │   └── Alert badges
│   │   └── QThread worker for recalculation
│   ├── SetHistoryWidget
│   │   └── QTableWidget with session timeline
│   └── EmptyStateWidget
│       └── Guidance labels
├── AudioPlayer (existing, shared)
└── RecommendationWorker (new QRunnable)
```

## State Machine

```
[EMPTY] ──load library──► [READY]
[READY] ──load next──► [PLAYING]
[PLAYING] ──load next──► [PLAYING] (self-loop, updates current)
[PLAYING] ──clear──► [READY]
[ANY] ──exit──► [HIDDEN]
```

## Key Classes

### `LiveAssistantScreen`
- Inherits `QWidget`
- Signals:
  - `exit_requested()` → MainWindow switches to Library tab
  - `preview_requested(path: str)` → MainWindow coordinates AudioPlayer

### `NowPlayingWidget`
- Inherits `QWidget`
- Displays current track metadata
- Contains `QTimer` for elapsed time display

### `SuggestionsWidget`
- Inherits `QWidget`
- Contains 3 `CandidateRow` widgets
- Manages `RecommendationWorker` lifecycle
- Updates UI when worker finishes

### `CandidateRow`
- Inherits `QWidget`
- Signals:
  - `load_next_requested(path: str)`
  - `preview_requested(path: str)`

### `SetHistoryWidget`
- Inherits `QWidget`
- Appends rows on each `load_next`

### `RecommendationWorker` (QRunnable)
- Runs `recommend_playlist` in background thread
- Emits `finished(result: RecommendationResult)` via `QMetaObject.invokeMethod`
- Handles cancellation if a newer request arrives

### `LiveAssistantState` (pure Python)
- Immutable state container
- No Qt dependency
- Fully unit-testable

## Threading Model

- Main thread: UI updates only
- Background thread: `recommend_playlist` execution via `QThreadPool`
- Cancellation: Each `RecommendationWorker` has a token; new request cancels previous

## Audio Preview Coordination

- `LiveAssistantScreen.preview_requested(path)` → `MainWindow._on_live_preview_requested(path)`
- MainWindow stops any playing preview, starts new one
- When preview finishes naturally, UI resets to ▶
- Same single-player coordination as LibraryScreen

## Keyboard Shortcuts

- Shortcuts registered on `LiveAssistantScreen` via `QShortcut`
- `Space`: emit `load_next_requested` for top candidate
- `1`, `2`, `3`: emit `load_next_requested` for candidate at index
- `Esc`: emit `exit_requested`

## Styling

- Dark background (`#1a1a2e`) for booth-friendly low-light visibility
- Large fonts (14-16pt) for readability at distance
- Alert badges: red `#ff4444`, yellow `#ffaa00`
- Current track highlight: blue `#4a90d9`

## Testing Strategy

- `test_live_assistant_state.py`: Pure state machine tests (no Qt)
- `test_live_assistant_screen.py`: Qt widget construction and signal tests
- `test_recommendation_worker.py`: Background thread behavior
- `test_main_window_live.py`: MainWindow integration (tab, shortcuts, audio coordination)
