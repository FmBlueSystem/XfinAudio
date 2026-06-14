# Spec: My Playlists Screen

## Capability

`my-playlists-screen`

## Intent

Provide a dedicated screen for managing saved playlists: listing, opening, renaming, duplicating, deleting.

## UI/UX Requirements

### Layout

- Left panel: list of saved playlists (name, track count, last modified)
- Right panel: playlist editor when a playlist is open
- Toolbar: New, Rename, Duplicate, Delete, Export buttons

### Playlist Editor

- Table showing tracks in order (Title, Artist, BPM, Key, Energy, Duration)
- Drag-and-drop to reorder
- Remove button per row
- "Add from Library" button to append tracks

### Empty State

When no playlists exist:
- Show message: "No saved playlists yet. Generate a playlist and click Save."

## Acceptance Criteria

### AC-1: Navigation

Given the user is in the Library screen
When they click "My Playlists"
Then the My Playlists screen opens.

### AC-2: Open playlist

Given the My Playlists list has items
When the user double-clicks a playlist
Then it opens in the editor.

### AC-3: Rename

Given a playlist is selected
When the user clicks Rename and enters a new name
Then the playlist is updated in the database and the list refreshes.

### AC-4: Duplicate

Given a playlist is selected
When the user clicks Duplicate
Then a new playlist with the same tracks and "(copy)" suffix is created.

### AC-5: Delete

Given a playlist is selected
When the user clicks Delete and confirms
Then the playlist is removed.

## Constraints

- Reuse existing table populator patterns.
- Reuse existing Serato export logic.
- Must follow strict TDD.
