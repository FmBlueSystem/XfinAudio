# Proposal: Playlist Persistence and Editing

## Context

XfinAudio currently generates playlists during a session but loses them on exit. DJs prepare sets over days or weeks and need to:

- Save generated playlists for later review and editing
- Maintain multiple set versions for the same gig
- Re-export a saved playlist to Serato at any time

## What

A full playlist persistence system:

1. **SQLite schema**: `playlists` table + `playlist_tracks` ordering table
2. **Domain model**: `Playlist` and `PlaylistTrack` records
3. **Repository**: `PlaylistRepository` for CRUD operations
4. **My Playlists screen**: list all saved playlists, open for edit, rename, duplicate, delete
5. **Playlist editor**: drag-and-drop reorder, add tracks from library, remove tracks
6. **Export integration**: export saved playlists to Serato from the editor

## Why

- Currently a playlist is generated, reviewed, exported… and lost.
- DJs prepare sets over days/weeks, not single sessions.
- Multiple set versions per gig is a common workflow.
- Bridge toward future Live Assistant mode (D) which needs persistent set state.

## Scope

### In scope
- Save playlist with name, created_at, updated_at
- Store ordered track references (by path)
- My Playlists screen with list view
- Open saved playlist in editor mode
- Add tracks from library into open playlist
- Remove tracks from playlist (not from library)
- Rename / duplicate / delete playlists
- Export saved playlist to Serato at any time
- Handle orphaned track references (show "missing" indicator)

### Out of scope
- Multi-software export (C) — deferred
- Live Assistant (D) — deferred until B ships
- Playlist folders/tags/categories
- Collaborative/shared playlists

## Technical approach
- Pure SQLite schema extension; no new dependencies
- `PlaylistRepository` alongside existing `TrackRepository`
- Playlist editor reuses `LibraryScreen` table patterns
- Drag-and-drop uses Qt `QTableWidget` native reordering

## Complexity
- Low-Medium

## Risk
- Low (pure SQLite, Qt native DnD)

## User impact
- High (closes the preparation loop)

## Sequence
This is Phase 2 of the XfinAudio evolution, following Audio Preview (A).
