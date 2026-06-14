# Design: Playlist Persistence

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│  MyPlaylistsScreen│────▶│ PlaylistRepository│────▶│  SQLite DB  │
│  (Qt Widget)      │     │  (pure Python)    │     │             │
└─────────────────┘     └──────────────────┘     └─────────────┘
         │
         ▼
┌─────────────────┐
│ PlaylistEditor  │
│ (QTableWidget)  │
└─────────────────┘
```

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS playlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS playlist_tracks (
    playlist_id INTEGER NOT NULL,
    track_path TEXT NOT NULL,
    position INTEGER NOT NULL,
    PRIMARY KEY (playlist_id, position),
    FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_playlist_tracks_playlist ON playlist_tracks(playlist_id);
```

## Domain Model

```python
@dataclass(frozen=True)
class Playlist:
    id: int | None  # None when not yet persisted
    name: str
    created_at: datetime
    updated_at: datetime
    track_paths: list[str]  # ordered

@dataclass(frozen=True)
class PlaylistSummary:
    id: int
    name: str
    track_count: int
    updated_at: datetime
```

## Repository API

```python
class PlaylistRepository:
    def create(self, name: str, track_paths: list[str]) -> Playlist: ...
    def list_summaries(self) -> list[PlaylistSummary]: ...
    def get_by_id(self, playlist_id: int) -> Playlist | None: ...
    def update_name(self, playlist_id: int, name: str) -> None: ...
    def update_tracks(self, playlist_id: int, track_paths: list[str]) -> None: ...
    def duplicate(self, playlist_id: int) -> Playlist: ...
    def delete(self, playlist_id: int) -> None: ...
```

## UI Design

### MyPlaylistsScreen

- `QSplitter` with left/right panels
- Left: `QListWidget` of playlists (custom item with name, count, date)
- Right: `PlaylistEditor` widget or empty state label

### PlaylistEditor

- `QTableWidget` with columns: #, Title, Artist, BPM, Key, Energy, Duration, Actions
- Drag-and-drop enabled via `setDragEnabled(True)` + `setAcceptDrops(True)`
- "Remove" button in Actions column
- Bottom toolbar: "Add from Library", "Export to Serato", "Save"

## Integration Points

- `MainWindow` creates `PlaylistRepository` alongside `TrackRepository`
- `MyPlaylistsScreen` emits `export_requested(playlist_id)` → `MainWindow` handles Serato export
- `LibraryScreen` emits `add_to_playlist_requested(paths)` → `PlaylistEditor` appends

## Error Handling

- Orphaned track paths: show "⚠ Missing" in Title cell, gray out row
- Empty playlist: disable export, show "Add tracks before exporting"
- Duplicate name: append "(1)", "(2)" etc.
