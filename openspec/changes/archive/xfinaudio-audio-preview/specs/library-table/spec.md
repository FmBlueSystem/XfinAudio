# Spec: Library Table (Audio Preview Extension)

## Capability

`library-table`

## Intent

Extend the existing library table to include a Preview column with play/pause controls and visual feedback for the currently playing track.

## Current State

The library table displays 10 columns: Title, Artist, BPM, Key, Energy, Duration, Missing, Genre, Status, Path. Columns are sortable (double-click header) and reorderable (drag header). Row selection drives the recommendation workflow.

## Changes

### New Column: Preview

A new column is added between "Status" and "Path" (or as the rightmost visible column if Path remains hidden). This column contains:

- A `QPushButton` with a play icon (▶) when the track is not playing.
- A `QPushButton` with a pause icon (⏸) when the track is the currently playing track.
- A disabled or hidden button when the track file is missing or the track is incomplete.

### Row Highlighting

When a track is playing:
- Its entire row receives a distinct background color (e.g., a subtle blue tint in light theme, a subtle highlight in dark theme).
- The highlight is removed when playback stops or another track starts playing.

### Signals Emitted

The `LibraryScreen` must emit:
- `play_requested(str path)` when the play button is clicked.
- `pause_requested()` when the pause button is clicked.

### State Update API

The `LibraryScreen` must provide:
- `set_playing_row(path: str | None)` — highlights the row matching the path, unhighlights all others.
- `set_row_error(path: str, message: str)` — shows a brief error indicator on the row.

## Acceptance Criteria

### AC-1: Preview column exists

Given the library table is visible
Then a "Preview" column is present with play/pause buttons on each row.

### AC-2: Play button triggers playback

Given a row has a play button
When the user clicks it
Then `play_requested(path)` is emitted with the track's file path.

### AC-3: Playing row is highlighted

Given `set_playing_row(path)` was called with a valid path
Then the matching row has a distinct highlight style.

### AC-4: Highlight cleared on stop

Given a row is highlighted as playing
When `set_playing_row(None)` is called
Then no row has the playing highlight.

### AC-5: No regression on existing columns

Given the library table has the Preview column
Then all existing columns (Title, Artist, BPM, Key, Energy, Duration, Missing, Genre, Status) continue to render correctly.
And sorting, filtering, and column reordering continue to work.

## UI/UX Requirements

- Play/pause buttons must be compact (max 24x24 px) to avoid cluttering the table.
- The Preview column width should be fixed and narrow ( ResizeToContents).
- Buttons must not steal focus from the table's row selection.

## Constraints

- Must use the existing table populator pattern for testability.
- Must not break existing tests for sorting, filtering, or column rendering.
- Must follow strict TDD.
