# Spec: Audio Preview

## Capability

`audio-preview`

## Intent

Provide lightweight audio playback of scanned tracks directly from the library table using PySide6 QMediaPlayer, allowing DJs to validate transitions by ear before including tracks in a playlist.

## User Story

As a DJ using XfinAudio, I want to click a Play button next to a track in my library so I can hear a preview of it, because metadata scores (BPM, key, energy) are not enough to know if a track will sound right in my set.

## Acceptance Criteria

### AC-1: Play a track from the library table

Given the library table is populated with scanned tracks
When the user clicks the Play button in a track's Preview column
Then audio playback of that track begins
And the track row is visually highlighted as "playing"
And the Play button changes to a Pause button.

### AC-2: Pause and resume playback

Given a track is currently playing
When the user clicks the Pause button
Then audio playback pauses
And the Pause button changes to a Play button.

When the user clicks the Play button again
Then audio playback resumes from the paused position.

### AC-3: Stop playback on track change

Given a track is currently playing or paused
When the user selects a different track in the library table
Then the current preview stops
And the previously playing row loses its highlight.

### AC-4: Single preview instance

Given a track is currently playing
When the user clicks Play on a different track
Then the first track's preview stops immediately
And the second track's preview begins.

### AC-5: Volume control

Given the preview player is active
When the user adjusts the volume slider
Then the playback volume changes accordingly.

And when the app is restarted
Then the volume is restored to the last used level.

### AC-6: Graceful error handling

Given a track file is missing, corrupted, or in an unsupported codec
When the user clicks Play
Then playback does not start
And the row shows a brief error indicator
And no exception or crash occurs.

## Functional Requirements

### FR-1: Player State Model

The player must expose an observable state machine with states: `IDLE`, `LOADING`, `PLAYING`, `PAUSED`, `ERROR`.

### FR-2: QMediaPlayer Backend

All audio decoding and playback must use `PySide6.QtMultimedia.QMediaPlayer` with `QAudioOutput`. No custom audio decoding.

### FR-3: Supported Formats

The player must support at minimum the same formats XfinAudio scans: MP3, FLAC, WAV, AIFF, M4A.

### FR-4: Position Tracking

The player must expose current playback position and total duration in milliseconds.

### FR-5: Seek Support

The player must support seeking to an arbitrary position within the track duration.

## Non-Functional Requirements

### NFR-1: UI Responsiveness

Audio playback must not block the Qt UI thread. `QMediaPlayer` handles playback in a background thread.

### NFR-2: Memory Efficiency

Only one `QMediaPlayer` instance exists at a time. No pre-loading of multiple tracks.

### NFR-3: Testability

Player state transitions must be testable without requiring audio output hardware (offscreen Qt tests).

### NFR-4: No Audio Mutation

The player is strictly read-only. No modification of audio files, metadata, or embedded tags occurs during playback.

## UI/UX Requirements

### UX-1: Play/Pause Icons

Use clear, universally understood icons (▶ / ⏸) for play and pause. Icons must be visible in both light and dark themes.

### UX-2: Playing Highlight

The currently playing row must have a distinct background color or border to make it immediately identifiable.

### UX-3: Keyboard Shortcut

Pressing Space while the library table is focused toggles play/pause for the selected track.

### UX-4: Error Feedback

Playback errors must show a non-intrusive indicator (tooltip or brief status message) rather than a blocking dialog.

## Constraints

- No new runtime dependencies beyond PySide6.
- No audio DSP, analysis, or detection.
- No waveform visualization in this slice.
- Must follow strict TDD (RED → GREEN → REFACTOR).

## Dependencies

- `PySide6.QtMultimedia` must be available in the current environment.
- Existing library scan service provides valid file paths.
- Existing settings persistence stores the volume value.

## Related Capabilities

- `library-table` (modified)
- `settings-persistence` (modified)
- `desktop-main-window` (modified)
