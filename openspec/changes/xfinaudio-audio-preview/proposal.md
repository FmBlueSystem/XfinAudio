# Proposal: XfinAudio Audio Preview

## Intent

Add a lightweight audio preview player inside XfinAudio so DJs can listen to tracks directly from the library table without leaving the app. This closes the most critical gap in the current workflow: a DJ sees metadata scores but cannot validate whether a transition "sounds" right without opening Serato or another player.

This change keeps XfinAudio read-only and metadata-first. It does not add audio DSP, waveform analysis, BPM/key detection, mixing, or mutation of audio files.

## Proposal Question Round

These questions are intentionally captured before implementation so the product decision points are explicit:

1. Should the preview player support scrubbing/seeking, or only play/pause with a position slider?
2. Should the player auto-stop when another track is selected, or allow multiple preview instances?
3. What is the maximum preview duration before the DJ should open the full track in their DJ software?
4. Should the player remember the last volume level across sessions?
5. Should the preview start from the beginning of the file, or from an existing cue point if metadata contains one?

### Assumptions for this SDD change

- Single preview instance only: selecting another track stops the current preview.
- Full seek/scrub support via `QMediaPlayer` position control.
- Preview starts from the beginning of the file (cue-point start is a future enhancement).
- Volume is persisted in app settings.
- Auto-stop on track change is the default behavior; no background audio continues unexpectedly.

## Scope

### In Scope

- Play / Pause / Stop controls per track row in the library table.
- Position slider with current time and total duration display.
- Volume slider persisted in app settings.
- Player state model (idle, loading, playing, paused, error) exposed to the UI.
- Error handling for unsupported files, missing files, or codec issues.
- Visual feedback: playing track highlighted, progress indicator.
- Settings persistence for last used volume.
- Strict TDD with offscreen Qt tests for player state and UI wiring.
- Controlled QA evidence: screenshot of player in library table, manual playback validation.

### Out of Scope

- Waveform visualization (requires DSP analysis — violates non-goals).
- Cue-point detection or reading from metadata (future enhancement).
- Multiple simultaneous previews (only one player instance).
- Playlist timeline scrubbing or crossfading (out of scope for preview).
- Audio effects, EQ, pitch-shift, time-stretch.
- Export of preview state to Serato or other DJ software.

## Capabilities

### New Capabilities

- `audio-preview`: Lightweight audio playback of scanned tracks directly from the library table using PySide6 QMediaPlayer.
- `player-state-model`: Observable player state (idle/loading/playing/paused/error) rendered in the library UI.
- `preview-settings-persistence`: Volume level persisted across app sessions.

### Modified Capabilities

- `desktop-main-window`: Coordinates player lifecycle and ensures only one active preview at a time.
- `library-table`: Adds play/pause action column and highlights the currently playing track.
- `settings-persistence`: Stores and restores the preview volume level.

## Approach

Use small, TDD-first slices. Build the player model first, then the Qt UI controls, then integrate into the library table, then add settings persistence and polish.

Keep the existing PySide6 desktop architecture:

- `MainWindow` coordinates the single player instance and stops preview on track change.
- `LibraryScreen` renders play/pause buttons and progress in the table.
- Pure player state logic stays outside Qt where possible.
- `QMediaPlayer` handles all actual audio playback; no custom audio code.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/xfinaudio/desktop/audio_player.py` | Created | Pure player state model and QMediaPlayer wrapper. |
| `src/xfinaudio/desktop/screens/library_screen.py` | Modified | Play/pause button column, playing-track highlight, progress display. |
| `src/xfinaudio/desktop/main_window.py` | Modified | Coordinates single player instance, stops on selection change. |
| `src/xfinaudio/desktop/library_view_model.py` | Modified | Exposes play action visibility and playing-state per row. |
| `src/xfinaudio/desktop/settings_dialog.py` | Modified | Volume setting if a global volume control is added. |
| `src/xfinaudio/config/settings.py` | Modified | `preview_volume` field in settings model. |
| `tests/` | Modified | Strict TDD tests for player state, UI wiring, settings persistence. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| QMediaPlayer fails on certain codecs (e.g., some FLAC or AIFF variants) | Medium | Graceful error handling with user-visible message; log unsupported format. |
| Audio playback causes UI lag or stutter | Low | QMediaPlayer runs in its own thread; UI is thin. |
| Preview state becomes inconsistent with rapid track selection | Medium | Defensive stop-before-play logic in MainWindow coordinator. |
| One large implementation overwhelms review | High | Use chained PR slices and the 400 changed-line review budget. |
| Settings migration for new volume field breaks existing configs | Low | Pydantic default value handles missing field gracefully. |

## Rollback Plan

Each PR slice is independently revertible:

1. Player model can be reverted without touching UI.
2. Library table column can be hidden/reverted without affecting scan/recommendation/export.
3. Settings volume field can be removed; existing configs fall back to default.
4. QA harness/docs can be removed without changing production behavior.

## Dependencies

- Current PySide6 desktop workflow remains the app entry point.
- Existing SQLite-backed track repository provides file paths for playback.
- `QMediaPlayer` is part of PySide6.QtMultimedia (verify availability in PySide6 6.11).
- Strict TDD is enabled in `openspec/config.yaml`.

## Success Criteria

- [ ] `uv run pytest -q` passes.
- [ ] `uv run ruff check .` passes.
- [ ] `uv run ruff format --check .` passes.
- [ ] Clicking Play on a track starts audio playback.
- [ ] Clicking Pause stops playback; clicking Resume continues from the same position.
- [ ] Selecting another track stops the current preview.
- [ ] Volume slider controls playback volume and persists across app restarts.
- [ ] Unsupported or missing files show a graceful error message (not a crash).
- [ ] The playing track is visually highlighted in the library table.
- [ ] Player state (idle/loading/playing/paused/error) is observable and testable without audio output.
