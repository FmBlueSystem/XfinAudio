# Spec: Live Assistant Mode

## Overview

A dedicated screen for live DJ performance that surfaces the current track, recommends the best next candidates, warns about risky transitions, and maintains a set history timeline.

## Functional Requirements

### FR-1: Now Playing Panel
- Display current track title, artist, BPM, Camelot key, energy level
- Display elapsed time since track was loaded (session timer)
- Show a prominent "Load Next" button for each candidate

### FR-2: Next Suggestions Panel
- Display top 3 candidate tracks from the library
- Each candidate shows: title, artist, BPM, key, energy, transition score
- Sort by transition score (highest first)
- Candidates must be from the current scanned library or a loaded playlist

### FR-3: Risk Alerts
- Red badge if BPM difference > 3%
- Red badge if key is not harmonically compatible (not adjacent Camelot wheel, not same key)
- Yellow badge if energy jump > 2 levels
- Alerts are purely visual; DJ can still choose any track

### FR-4: Load Next Action
- Clicking "Load Next" on a candidate:
  - Moves current track to set history
  - Sets candidate as new current track
  - Recalculates top 3 suggestions based on new current track
  - Appends to session history with timestamp

### FR-5: Set History Timeline
- Vertical list of tracks loaded in this session
- Each entry shows: order number, title, artist, BPM, key, time loaded
- Scrollable; no limit on session length

### FR-6: Auto-advance Suggestions
- When a new track becomes current, automatically recalculate suggestions
- Use existing recommendation engine with `build` strategy and current track as anchor
- Limit candidate pool to 25 tracks (same as existing)

### FR-7: Audio Preview Integration
- Each candidate row has a ▶/⏸ preview button
- Uses existing `AudioPlayer`; single-player coordination applies
- Previewing a candidate does not affect "current track" state

### FR-8: Playlist Load
- DJ can load a saved playlist into Live Assistant
- Playlist tracks become the candidate pool
- Current track starts as the first track in the playlist

### FR-9: Keyboard Shortcuts
- `Space`: Load the top-ranked candidate (if focus is in Live Assistant)
- `Esc`: Exit Live Assistant and return to Library tab
- `1`, `2`, `3`: Load candidate 1, 2, or 3 respectively

### FR-10: Empty State
- If no library is loaded, show guidance: "Scan or load a playlist to start Live Assistant"
- If only one track in library, show: "At least 2 tracks needed for suggestions"

## Non-Functional Requirements

- NFR-1: Suggestion recalculation must complete within 500ms for 100-track libraries
- NFR-2: UI must remain responsive during recalculation (use background thread)
- NFR-3: Session history is not persisted across app restarts (in-memory only)
- NFR-4: Screen must work at minimum window size (800x600)

## Data Model

### SessionTrack
```python
@dataclass
class SessionTrack:
    track: TrackRecord
    loaded_at: datetime
    order: int
```

### LiveAssistantState
```python
@dataclass
class LiveAssistantState:
    current_track: TrackRecord | None
    candidates: list[TrackRecord]
    history: list[SessionTrack]
    alert_flags: list[RiskAlert]
```

### RiskAlert
```python
@dataclass
class RiskAlert:
    track_path: str
    alert_type: Literal["bpm_guardrail", "key_clash", "energy_jump"]
    message: str
```

## UI Layout

```
+----------------------------------------------------------+
|  LIVE ASSISTANT                              [Exit]      |
+----------------------------------------------------------+
|  NOW PLAYING                                             |
|  +----------------------------------------------------+  |
|  | Title    | Artist   | BPM  | Key  | Energy | Timer |  |
|  | Song A   | Artist A | 128  | 11B  | 7      | 2:34  |  |
|  +----------------------------------------------------+  |
+----------------------------------------------------------+
|  NEXT SUGGESTIONS                                        |
|  +----------------------------------------------------+  |
|  | # | Title   | Artist  | BPM | Key | Energy | Score |  |
|  | 1 | Song B  | Artist B| 129 | 12B | 7      | 0.95  |  |
|  |   | [▶] [Load Next]        [BPM OK] [Key OK]        |  |
|  | 2 | Song C  | Artist C| 125 | 11A | 6      | 0.82  |  |
|  |   | [▶] [Load Next]        [⚠ Energy -2]            |  |
|  | 3 | Song D  | Artist D| 135 | 3A  | 8      | 0.71  |  |
|  |   | [▶] [Load Next]        [⚠ BPM +5.5%] [⚠ Key]   |  |
|  +----------------------------------------------------+  |
+----------------------------------------------------------+
|  SET HISTORY                                             |
|  +----------------------------------------------------+  |
|  | 1 | Song A | Artist A | 128 | 11B | 14:32:05       |  |
|  | 2 | Song B | Artist B | 129 | 12B | 14:35:12       |  |
|  +----------------------------------------------------+  |
+----------------------------------------------------------+
```

## Dependencies

- `recommend_playlist` from `xfinaudio.recommendation.playlist_service`
- `AudioPlayer` from `xfinaudio.desktop.audio_player`
- `PlaylistRepository` from `xfinaudio.library.playlist_repository`
- `TrackRecord` from `xfinaudio.library.models`

## Error Handling

- If recommendation engine raises, show "Suggestions unavailable" and log error
- If candidate pool is empty, show "No compatible tracks found"
- If audio preview fails, show error inline on the candidate row
