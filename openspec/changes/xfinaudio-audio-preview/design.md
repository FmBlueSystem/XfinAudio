# Design: XfinAudio Audio Preview

## Technical Approach

This change adds a lightweight audio preview player using PySide6's built-in `QMediaPlayer`. The architecture remains read-only and metadata-first: `QMediaPlayer` handles all audio I/O; XfinAudio code only manages player state, UI wiring, and settings persistence.

Implementation order:

1. Verify `QMediaPlayer` availability and create the pure player state model.
2. Create the player wrapper with QMediaPlayer backend and observable state.
3. Integrate play/pause controls into the library table.
4. Add single-player coordination in MainWindow (stop on track change).
5. Add volume persistence to settings.
6. Add error handling and user-visible feedback.
7. Record final QA evidence.

## Architecture Decisions

### Decision: Use QMediaPlayer from PySide6.QtMultimedia

**Choice:** Use `QMediaPlayer` + `QAudioOutput` from PySide6.QtMultimedia for all audio playback.
**Alternatives considered:** Custom FFmpeg wrapper; `pygame.mixer`; external process playback.
**Rationale:** `QMediaPlayer` is built into PySide6, requires no new dependencies, supports all common audio formats (MP3, AAC, FLAC, WAV, AIFF), and handles decoding/playback in a separate thread. It is the standard Qt multimedia solution.

### Decision: Single player instance coordinated by MainWindow

**Choice:** Only one `QMediaPlayer` instance exists; `MainWindow` stops current playback before starting a new one.
**Alternatives considered:** One player per table row; lazy player creation per track.
**Rationale:** Multiple simultaneous audio streams would confuse the DJ and consume unnecessary resources. A single instance is simpler, predictable, and testable.

### Decision: Player state model is pure and observable

**Choice:** Extract player state transitions into a pure model class that emits signals; the Qt wrapper delegates to `QMediaPlayer` but state logic is testable without audio hardware.
**Alternatives considered:** Embed all logic directly in Qt widget callbacks.
**Rationale:** Pure state logic can be unit-tested without relying on `QMediaPlayer`'s async media status changes. The Qt layer becomes a thin adapter.

### Decision: Volume is a setting, not a per-track property

**Choice:** Persist one global preview volume in app settings; do not store per-track volume.
**Alternatives considered:** Per-track volume; per-session volume only.
**Rationale:** A DJ typically wants consistent preview loudness across all tracks. One setting is simpler and matches user expectations.

### Decision: Use chained PRs

**Choice:** Treat this as a chained PR sequence because the change spans a new module, UI modifications, settings changes, and tests.
**Alternatives considered:** One large PR with `size:exception`.
**Rationale:** Player model, UI integration, and settings are independent layers that can be reviewed separately. This protects reviewer cognition and rollback control.

## Data Flow

Player lifecycle:

```text
User clicks Play on track row
  -> LibraryScreen emits play_requested(path)
  -> MainWindow stops current preview (if any)
  -> MainWindow calls player.load(path)
  -> Player state: idle -> loading
  -> QMediaPlayer loads media
  -> QMediaPlayer signals loaded -> Player state: loaded -> playing
  -> LibraryScreen highlights playing track, shows pause button
  -> User clicks Pause
  -> Player state: playing -> paused
  -> User clicks Play again
  -> Player state: paused -> playing (resumes position)
  -> User selects another track
  -> MainWindow stops player
  -> Player state: playing/paused -> idle
```

Settings flow:

```text
Settings loaded
  -> preview_volume restored (default 0.7 if missing)
  -> Player volume set on initialization
  -> User changes volume slider
  -> Settings saved with new volume
```

Error flow:

```text
QMediaPlayer encounters error
  -> Player state: loading/playing -> error
  -> LibraryScreen shows error indicator on row
  -> Error message logged and optionally shown to user
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/xfinaudio/desktop/audio_player.py` | Create | `AudioPlayer` class wrapping QMediaPlayer with observable state (idle/loading/playing/paused/error). |
| `src/xfinaudio/desktop/audio_player_state.py` | Create | Pure player state enum and state machine (testable without Qt). |
| `src/xfinaudio/desktop/screens/library_screen.py` | Modify | Add play/pause action column; highlight playing track; render progress/state. |
| `src/xfinaudio/desktop/main_window.py` | Modify | Coordinate single player instance; stop on selection change; wire play signals. |
| `src/xfinaudio/desktop/library_view_model.py` | Modify | Expose per-row playing state and action visibility. |
| `src/xfinaudio/config/settings.py` | Modify | Add `preview_volume: float = 0.7` to settings model. |
| `src/xfinaudio/desktop/settings_dialog.py` | Modify | Optional: add global volume slider in Settings. |
| `tests/test_audio_player_state.py` | Create | Unit tests for pure state transitions. |
| `tests/test_audio_player.py` | Create | Qt-offscreen tests for player wrapper and QMediaPlayer wiring. |
| `tests/test_library_screen_preview.py` | Create | Tests for library table preview column and state rendering. |
| `tests/test_main_window.py` | Modify | Tests for MainWindow player coordination (stop-on-change, single instance). |
| `tests/test_settings.py` | Modify | Tests for preview_volume settings persistence. |
| `scripts/capture_desktop_screens.py` | Create/Modify | Screenshot evidence of player in library table. |

## Interfaces / Contracts

### AudioPlayer contract

```python
class AudioPlayer(QObject):
    state_changed = Signal(PlayerState)  # idle, loading, playing, paused, error
    position_changed = Signal(int)       # milliseconds
    duration_changed = Signal(int)       # milliseconds
    error_occurred = Signal(str)         # error message

    def load(self, path: str) -> None: ...
    def play(self) -> None: ...
    def pause(self) -> None: ...
    def stop(self) -> None: ...
    def set_volume(self, volume: float) -> None: ...  # 0.0 - 1.0
    def seek(self, position_ms: int) -> None: ...
    @property
    def state(self) -> PlayerState: ...
    @property
    def position_ms(self) -> int: ...
    @property
    def duration_ms(self) -> int: ...
```

### PlayerState contract

```python
class PlayerState(Enum):
    IDLE = "idle"
    LOADING = "loading"
    PLAYING = "playing"
    PAUSED = "paused"
    ERROR = "error"
```

State transitions:

```
IDLE --load()--> LOADING --loaded--> PLAYING
PLAYING --pause()--> PAUSED
PAUSED --play()--> PLAYING
PLAYING/PAUSED/LOADING --stop()--> IDLE
ANY --error()--> ERROR
ERROR --load()--> LOADING
```

### Library table contract

```python
# Row data includes playing state for rendering
class LibraryRow:
    ...
    is_playing: bool
    is_paused: bool
    play_progress_pct: float | None  # 0.0 - 1.0
```

### Settings contract

```python
class AppSettings(BaseModel):
    ...
    preview_volume: float = Field(default=0.7, ge=0.0, le=1.0)
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `PlayerState` transitions | Pure Python tests; no Qt required. |
| Unit | `AudioPlayer` state machine | Qt-offscreen tests with a mock/dummy media file. |
| Qt/offscreen | Library table preview column | `tests/test_library_screen_preview.py` with offscreen Qt. |
| Qt/offscreen | MainWindow player coordination | `tests/test_main_window.py` — stop on selection change, single instance. |
| Integration | Settings persistence | `tests/test_settings.py` — volume save/load round-trip. |
| QA | Screenshots and manual review | Capture evidence and inspect player visibility and feedback. |

## Migration / Rollout

No data migration required. Roll out through chained PR slices:

1. Player model and state machine (pure + Qt wrapper).
2. Library table integration (play/pause column + highlight).
3. MainWindow coordination (single instance, stop-on-change).
4. Settings persistence (volume save/load).
5. Error handling and polish.
6. Final QA evidence.

## Open Questions

- [ ] PySide6.QtMultimedia availability must be verified in the current venv.
- [ ] Whether to add a global volume slider in Settings or only per-player volume.
- [ ] Whether to show a waveform placeholder or keep the UI minimal for this slice.
