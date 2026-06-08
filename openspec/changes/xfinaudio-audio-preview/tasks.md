# Tasks: XfinAudio Audio Preview

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 800-1400 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 player model -> PR 2 library table integration -> PR 3 MainWindow coordination -> PR 4 settings persistence -> PR 5 error handling + polish -> PR 6 QA evidence |
| Delivery strategy | auto-chain |
| Chain strategy | feature-branch-chain |

Decision needed before apply: No
Chained PRs recommended: Yes
400-line budget risk: High
Chain strategy: feature-branch-chain

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Player state model + AudioPlayer wrapper | PR 1 | Pure state + Qt wrapper with QMediaPlayer. |
| 2 | Library table preview column | PR 2 | Play/pause button, highlight, progress. |
| 3 | MainWindow single-player coordination | PR 3 | Stop-on-change, signal wiring. |
| 4 | Settings volume persistence | PR 4 | preview_volume field + Settings dialog. |
| 5 | Error handling + UI polish | PR 5 | Graceful errors, empty states, visual feedback. |
| 6 | Final desktop QA evidence | PR 6 | Screenshots, manual playback validation, verify-report. |

---

## Phase 1: Player State Model

### 1.1 RED: Add `tests/test_audio_player_state.py`

- [ ] 1.1.1 Create `tests/test_audio_player_state.py` with tests for `PlayerState` enum.
- [ ] 1.1.2 Test valid state transitions: `idle -> loading -> playing -> paused -> playing -> idle`.
- [ ] 1.1.3 Test error transition: `loading -> error` and `error -> loading`.
- [ ] 1.1.4 Run tests and confirm they fail with `ModuleNotFoundError` for `xfinaudio.desktop.audio_player_state`.

### 1.2 GREEN: Create `src/xfinaudio/desktop/audio_player_state.py`

- [ ] 1.2.1 Create `PlayerState` enum with `IDLE`, `LOADING`, `PLAYING`, `PAUSED`, `ERROR`.
- [ ] 1.2.2 Create `PlayerStateMachine` class with `transition(event) -> PlayerState`.
- [ ] 1.2.3 Define valid transitions in a dictionary; reject invalid transitions.
- [ ] 1.2.4 Run `tests/test_audio_player_state.py` and confirm all pass.

### 1.3 RED: Add `tests/test_audio_player.py` (Qt wrapper)

- [ ] 1.3.1 Create `tests/test_audio_player.py` with offscreen Qt tests.
- [ ] 1.3.2 Test `AudioPlayer` instantiation emits `state_changed(IDLE)`.
- [ ] 1.3.3 Test `load(path)` transitions state to `LOADING` then `PLAYING` (mock or use a small test audio file).
- [ ] 1.3.4 Test `pause()` transitions `PLAYING -> PAUSED`.
- [ ] 1.3.5 Test `play()` from `PAUSED` transitions to `PLAYING`.
- [ ] 1.3.6 Test `stop()` transitions any state to `IDLE`.
- [ ] 1.3.7 Test `set_volume(0.5)` sets volume without state change.
- [ ] 1.3.8 Run tests and confirm they fail with `ModuleNotFoundError` for `xfinaudio.desktop.audio_player`.

### 1.4 GREEN: Create `src/xfinaudio/desktop/audio_player.py`

- [ ] 1.4.1 Create `AudioPlayer` class extending `QObject`.
- [ ] 1.4.2 Instantiate `QMediaPlayer` and `QAudioOutput` internally.
- [ ] 1.4.3 Wire `QMediaPlayer.mediaStatusChanged` to update internal state machine.
- [ ] 1.4.4 Implement `load()`, `play()`, `pause()`, `stop()`, `set_volume()`, `seek()`.
- [ ] 1.4.5 Emit `state_changed`, `position_changed`, `duration_changed`, `error_occurred` signals.
- [ ] 1.4.6 Run `tests/test_audio_player.py` and confirm all pass.

### 1.5 REFACTOR: Clean player model/wrapper

- [ ] 1.5.1 Ensure `AudioPlayer` has no direct dependency on `MainWindow` or `LibraryScreen`.
- [ ] 1.5.2 Ensure `PlayerStateMachine` is pure Python (no Qt import).
- [ ] 1.5.3 Run full test suite: `uv run pytest tests/test_audio_player_state.py tests/test_audio_player.py -q`.

---

## Phase 2: Library Table Preview Column

### 2.1 RED: Add library preview column tests

- [ ] 2.1.1 Create `tests/test_library_screen_preview.py` with offscreen Qt tests.
- [ ] 2.1.2 Test that library table has a "Preview" column with play/pause buttons.
- [ ] 2.1.3 Test that clicking Play emits a signal with the track path.
- [ ] 2.1.4 Test that the playing track row has a highlighted style.
- [ ] 2.1.5 Test that a paused track shows a pause icon.
- [ ] 2.1.6 Run tests and confirm they fail (column does not exist yet).

### 2.2 GREEN: Add preview column to library table

- [ ] 2.2.1 Modify `src/xfinaudio/desktop/screens/library_screen.py` to add a Preview column.
- [ ] 2.2.2 Add `QPushButton` (play icon) to each row's Preview cell.
- [ ] 2.2.3 Emit `play_requested(path)` signal when play button is clicked.
- [ ] 2.2.4 Emit `pause_requested()` signal when pause button is clicked.
- [ ] 2.2.5 Add method `set_playing_row(path | None)` to highlight/unhighlight rows.
- [ ] 2.2.6 Run `tests/test_library_screen_preview.py` and confirm pass.

### 2.3 REFACTOR: Keep table populators testable

- [ ] 2.3.1 Ensure preview button factory is injectable (same pattern as existing table populators).
- [ ] 2.3.2 Ensure no hard dependency on `AudioPlayer` from `LibraryScreen`.
- [ ] 2.3.3 Run existing library table tests to confirm no regression.

---

## Phase 3: MainWindow Single-Player Coordination

### 3.1 RED: Add MainWindow player coordination tests

- [ ] 3.1.1 Add tests to `tests/test_main_window.py`:
  - Test that `MainWindow` creates one `AudioPlayer` instance.
  - Test that `play_requested` signal loads and plays the track.
  - Test that selecting another track stops current playback.
  - Test that `pause_requested` signal pauses playback.
- [ ] 3.1.2 Run tests and confirm they fail.

### 3.2 GREEN: Wire player into MainWindow

- [ ] 3.2.1 Modify `src/xfinaudio/desktop/main_window.py` to instantiate `AudioPlayer`.
- [ ] 3.2.2 Connect `LibraryScreen.play_requested` to `MainWindow._on_play_requested(path)`.
- [ ] 3.2.3 In `_on_play_requested`, stop current preview before loading new track.
- [ ] 3.2.4 Connect `LibraryScreen.pause_requested` to `AudioPlayer.pause()`.
- [ ] 3.2.5 Connect `AudioPlayer.state_changed` to `LibraryScreen.set_playing_row(path | None)`.
- [ ] 3.2.6 On track selection change (existing signal), stop player if selection changes.
- [ ] 3.2.7 Run `tests/test_main_window.py` and confirm pass.

### 3.3 REFACTOR: Defensive single-player logic

- [ ] 3.3.1 Ensure `MainWindow` does not leak `AudioPlayer` references to screens.
- [ ] 3.3.2 Ensure player is stopped before app exit (`closeEvent`).
- [ ] 3.3.3 Run full test suite: `uv run pytest -q`.

---

## Phase 4: Settings Volume Persistence

### 4.1 RED: Add settings volume tests

- [ ] 4.1.1 Add test to `tests/test_settings.py`: default `preview_volume` is `0.7`.
- [ ] 4.1.2 Add test: saving settings with `preview_volume=0.3` and reloading restores `0.3`.
- [ ] 4.1.3 Run tests and confirm they fail (field does not exist).

### 4.2 GREEN: Add preview_volume to settings

- [ ] 4.2.1 Modify `src/xfinaudio/config/settings.py` to add `preview_volume: float = Field(default=0.7, ge=0.0, le=1.0)`.
- [ ] 4.2.2 Modify `src/xfinaudio/desktop/main_window.py` to read `preview_volume` on startup and call `player.set_volume()`.
- [ ] 4.2.3 Optional: add volume slider to `SettingsDialog`.
- [ ] 4.2.4 Run `tests/test_settings.py` and confirm pass.

### 4.3 REFACTOR: Settings backward compatibility

- [ ] 4.3.1 Verify that existing `settings.json` without `preview_volume` loads with default `0.7`.
- [ ] 4.3.2 Run full test suite: `uv run pytest -q`.

---

## Phase 5: Error Handling and Polish

### 5.1 RED: Add error handling tests

- [ ] 5.1.1 Add test: `AudioPlayer` emits `error_occurred` when `QMediaPlayer` signals an error.
- [ ] 5.1.2 Add test: library table shows error indicator when playback fails.
- [ ] 5.1.3 Run tests and confirm they fail.

### 5.2 GREEN: Implement error handling

- [ ] 5.2.1 Wire `QMediaPlayer.errorOccurred` to `AudioPlayer._on_media_error()`.
- [ ] 5.2.2 Transition state to `ERROR` and emit `error_occurred(message)`.
- [ ] 5.2.3 In `LibraryScreen`, show a brief error tooltip or red icon on the failed row.
- [ ] 5.2.4 Log error details for debugging.
- [ ] 5.2.5 Run tests and confirm pass.

### 5.3 GREEN: UI polish

- [ ] 5.3.1 Ensure play/pause icons are clear and translatable.
- [ ] 5.3.2 Ensure playing track highlight is visible in both light and dark themes.
- [ ] 5.3.3 Add keyboard shortcut (Space) for play/pause when library table is focused.
- [ ] 5.3.4 Verify i18n strings are marked with `self.tr()`.

### 5.4 REFACTOR: Clean integration

- [ ] 5.4.1 Remove any debug prints or temporary code.
- [ ] 5.4.2 Ensure `ruff check .` and `ruff format --check .` pass.
- [ ] 5.4.3 Run full test suite: `uv run pytest -q`.

---

## Phase 6: Final QA Evidence

### 6.1 Automated gates

- [ ] 6.1.1 Run `uv run pytest -q`.
- [ ] 6.1.2 Run `uv run ruff check .`.
- [ ] 6.1.3 Run `uv run ruff format --check .`.
- [ ] 6.1.4 Run `uv run python scripts/release_gate_check.py --run` or record blocker.

### 6.2 Manual QA

- [ ] 6.2.1 Launch app, scan a real music folder.
- [ ] 6.2.2 Click Play on a track; confirm audio plays.
- [ ] 6.2.3 Click Pause; confirm audio pauses.
- [ ] 6.2.4 Click Play again; confirm audio resumes.
- [ ] 6.2.5 Select another track; confirm previous preview stops.
- [ ] 6.2.6 Adjust volume; confirm it persists after app restart.
- [ ] 6.2.7 Test with MP3, FLAC, WAV, AIFF, M4A files.
- [ ] 6.2.8 Test with a missing/corrupt file; confirm graceful error (no crash).

### 6.3 Screenshot evidence

- [ ] 6.3.1 Capture screenshot of library table with Play buttons visible.
- [ ] 6.3.2 Capture screenshot of playing track with highlight.
- [ ] 6.3.3 Capture screenshot of error state (if reproducible with a test file).

### 6.4 Verify report

- [ ] 6.4.1 Create `verify-report.md` with requirement-by-requirement evidence.

---

## Commit Boundaries

Use conventional commits only. Never add AI attribution. Use feature-branch-chain: PR 1 targets the tracker branch, each later PR targets the immediate previous PR branch, and only the tracker branch merges to main.

- PR 1: `feat: add audio player state model and QMediaPlayer wrapper`
- PR 2: `feat: add preview play/pause column to library table`
- PR 3: `feat: coordinate single audio player instance in MainWindow`
- PR 4: `feat: persist preview volume in app settings`
- PR 5: `feat: add error handling and polish for audio preview`
- PR 6: `test: add audio preview QA evidence and verify report`
