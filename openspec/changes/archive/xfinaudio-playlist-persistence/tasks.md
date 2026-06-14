# Tasks: XfinAudio Playlist Persistence

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 1000-1600 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 schema+model+repo → PR 2 MyPlaylists screen → PR 3 PlaylistEditor → PR 4 MainWindow integration → PR 5 QA evidence |
| Delivery strategy | auto-chain |
| Chain strategy | feature-branch-chain |

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Database schema + Playlist model + PlaylistRepository | PR 1 | Pure data layer, no Qt |
| 2 | MyPlaylistsScreen (list view) | PR 2 | List widget, CRUD operations |
| 3 | PlaylistEditor widget | PR 3 | Table with DnD, add/remove |
| 4 | MainWindow integration + export wiring | PR 4 | Navigation, signals, Serato export |
| 5 | Final QA evidence | PR 5 | Tests, verify report |

---

## Unit 1: Schema, Model, Repository

### 1.1 RED: Add tests for Playlist model

- [x] 1.1.1 Create `tests/test_playlist_model.py`
- [x] 1.1.2 Test Playlist construction with id, name, created_at, updated_at, track_paths
- [x] 1.1.3 Test PlaylistSummary construction
- [x] 1.1.4 Run and confirm failures

### 1.2 GREEN: Create Playlist model

- [x] 1.2.1 Create `src/xfinaudio/library/playlist_models.py` with `Playlist` and `PlaylistSummary`

### 1.3 RED: Add tests for PlaylistRepository

- [x] 1.3.1 Create `tests/test_playlist_repository.py`
- [x] 1.3.2 Test create, list_summaries, get_by_id, update_name, update_tracks, duplicate, delete
- [x] 1.3.3 Test orphaned track paths (track not in DB) still returned
- [x] 1.3.4 Run and confirm failures

### 1.4 GREEN: Create PlaylistRepository

- [x] 1.4.1 Create `src/xfinaudio/library/playlist_repository.py`
- [x] 1.4.2 Implement all CRUD methods
- [x] 1.4.3 Add schema to `_ensure_schema` in TrackRepository (or create shared schema manager)
- [x] 1.4.4 Run tests and confirm pass

### 1.5 REFACTOR

- [x] 1.5.1 Extract shared schema initialization if needed
- [x] 1.5.2 Ensure no SQL injection (parameterized queries only)

---

## Unit 2: MyPlaylistsScreen

### 2.1 RED: Add MyPlaylistsScreen tests

- [x] 2.1.1 Create `tests/test_my_playlists_screen.py`
- [x] 2.1.2 Test screen constructs without error
- [x] 2.1.3 Test list_populate emits correct data
- [x] 2.1.4 Test double-click emits open_requested
- [x] 2.1.5 Run and confirm failures

### 2.2 GREEN: Create MyPlaylistsScreen

- [x] 2.2.1 Create `src/xfinaudio/desktop/screens/my_playlists_screen.py`
- [x] 2.2.2 Build list view with custom items
- [x] 2.2.3 Add rename/duplicate/delete buttons
- [x] 2.2.4 Emit signals: open_requested, create_requested, rename_requested, duplicate_requested, delete_requested

### 2.3 REFACTOR

- [x] 2.3.1 Ensure i18n with `self.tr()`
- [x] 2.3.2 Ensure no hard dependency on repository (signals only)

---

## Unit 3: PlaylistEditor

### 3.1 RED: Add PlaylistEditor tests

- [x] 3.1.1 Create `tests/test_playlist_editor.py`
- [x] 3.1.2 Test constructs with playlist data
- [x] 3.1.3 Test set_playlist populates table
- [x] 3.1.4 Test remove_row emits track_removed
- [x] 3.1.5 Run and confirm failures

### 3.2 GREEN: Create PlaylistEditor

- [x] 3.2.1 Create `src/xfinaudio/desktop/screens/playlist_editor.py`
- [x] 3.2.2 Build QTableWidget with track columns
- [x] 3.2.3 Add remove button per row
- [x] 3.2.4 Emit signals: track_removed, tracks_reordered, export_requested, save_requested

### 3.3 REFACTOR

- [x] 3.3.1 Ensure drag-and-drop enabled
- [x] 3.3.2 Handle missing tracks with ⚠ indicator

---

## Unit 4: MainWindow Integration

### 4.1 RED: Add integration tests

- [x] 4.1.1 Create `tests/test_main_window_playlists.py`
- [x] 4.1.2 Test MainWindow creates PlaylistRepository
- [x] 4.1.3 Test playlist creation flow
- [x] 4.1.4 Run and confirm failures

### 4.2 GREEN: Wire into MainWindow

- [x] 4.2.1 Add My Playlists tab to MainWindow
- [x] 4.2.2 Connect MyPlaylistsScreen signals to repository
- [x] 4.2.3 Connect PlaylistEditor signals to repository
- [x] 4.2.4 Wire export button to existing Serato export logic
- [x] 4.2.5 Add "Save Playlist" button to Build/Review screens

### 4.3 REFACTOR

- [x] 4.3.1 Ensure no memory leaks (parent widgets set)
- [x] 4.3.2 Ensure closeEvent handles any background operations

---

## Unit 5: QA Evidence

### 5.1 Automated gates

- [x] 5.1.1 Run `uv run pytest -q` → **683 passed, 0 failed**
- [x] 5.1.2 Run `uv run ruff check .` → Pre-existing errors only; new files clean
- [x] 5.1.3 Run `uv run ruff format --check .` → Clean

### 5.2 Verify report

- [x] 5.2.1 Create `verify-report.md`

---

## Files Changed

### New files
- `src/xfinaudio/library/playlist_models.py`
- `src/xfinaudio/library/playlist_repository.py`
- `src/xfinaudio/desktop/screens/my_playlists_screen.py`
- `src/xfinaudio/desktop/screens/playlist_editor.py`
- `tests/test_playlist_model.py`
- `tests/test_playlist_repository.py`
- `tests/test_my_playlists_screen.py`
- `tests/test_playlist_editor.py`
- `tests/test_main_window_playlists.py`

### Modified files
- `src/xfinaudio/desktop/main_window.py`
- `src/xfinaudio/desktop/screens/__init__.py`
- `tests/test_main_window.py`
- `tests/test_visual_integration.py`
