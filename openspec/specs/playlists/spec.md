# Spec: Playlist Persistence

## Capability

`playlist-persistence`

## Intent

Persist generated playlists into the SQLite database so DJs can return later, edit, rename, and re-export.

## User Story

As a DJ, I want to save a generated playlist so I can refine it over multiple sessions before exporting to Serato.

## Acceptance Criteria

### AC-1: Save a playlist

Given a playlist has been generated
When the user clicks "Save Playlist"
Then a dialog prompts for a name
And the playlist is stored in the database with ordered track references
And a timestamp is recorded.

### AC-2: List saved playlists

Given the user opens "My Playlists"
Then a list of all saved playlists is shown with name, track count, and last modified date.

### AC-3: Open a playlist for editing

Given a saved playlist exists
When the user selects it
Then the playlist opens in edit mode with tracks in saved order.

### AC-4: Reorder tracks

Given a playlist is in edit mode
When the user drags a track to a new position
Then the track order is updated.

### AC-5: Remove a track

Given a playlist is in edit mode
When the user clicks remove on a track
Then the track is removed from the playlist but not from the library.

### AC-6: Add tracks from library

Given a playlist is in edit mode
When the user selects tracks from the library and clicks "Add to Playlist"
Then those tracks are appended to the playlist.

### AC-7: Rename / duplicate / delete

Given a saved playlist exists
When the user renames it, the new name persists.
When the user duplicates it, a copy with "(copy)" suffix is created.
When the user deletes it, the playlist is removed from the database.

### AC-8: Export saved playlist

Given a saved playlist is open
When the user clicks "Export to Serato"
Then the playlist is exported using the existing Serato crate writer.

### AC-9: Handle missing tracks

Given a saved playlist references a track that no longer exists
When the playlist is loaded
Then the track shows a "missing" indicator and is skipped during export.

### AC-10: Repository contract boundary

Given desktop or application orchestration needs saved-playlist persistence
When it depends on playlist storage
Then it uses the explicit playlist repository port contract
And concrete SQLite repository behavior remains an infrastructure detail.

## Data Model

### Playlist

- `id: INTEGER PRIMARY KEY AUTOINCREMENT`
- `name: TEXT NOT NULL`
- `created_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP`
- `updated_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP`

### PlaylistTrack

- `playlist_id: INTEGER NOT NULL`
- `track_path: TEXT NOT NULL`
- `position: INTEGER NOT NULL`
- `PRIMARY KEY (playlist_id, position)`
- `FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE`

## Constraints

- No new runtime dependencies.
- Must follow strict TDD (RED → GREEN → REFACTOR).
