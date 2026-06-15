# Fagan Inspection: Playlist Persistence & App Audit

**Date:** 2026-06-14  
**Inspector:** opencode (sdd-apply) for Freddy Molina  
**Scope:** Generated playlist persistence (the user's reported issue) + broad app anomaly hunt  
**Framework:** Fagan Inspection (Planning -> Overview -> Individual Preparation -> Inspection Meeting -> Rework -> Follow-up)

---

## 1. Planning

**Defect categories targeted:**
- D1: Recommendation-to-playlist bridge (the user's reported issue).
- D2: Dead UI affordances (buttons that do nothing).
- D3: Export pipeline defects (I/O errors, missing directories).
- D4: Architectural inconsistencies (dual tables, dual state owners).
- D5: UX promise mismatches (empty-state text that promises an action that does not exist).

**Severity scale:** Critical (blocks primary workflow) / Medium (degrades UX, causes confusion) / Low (cosmetic or edge case).

---

## 2. Overview

**Recommendation flow (intended):**
Library -> Build Playlist -> Recommend -> Review Mix -> Export to Serato.

**Playlist persistence flow (intended, per empty-state copy):**
"Generate a playlist and click Save." This promise is on `MyPlaylistsScreen` line 56.

**Actual current flow:**
There is NO bridge from the generated recommendation (`state.last_recommendation`) to a row in the `playlist_repository` table. The only way to create a playlist is `PlaylistCoordinator.create_playlist`, which creates an EMPTY playlist (line 76).

---

## 3. Individual Preparation — Findings

### F1. [Critical] Generated playlists are never saved to My Playlists

**Location:** `src/xfinaudio/desktop/main_window.py`, `src/xfinaudio/desktop/playlist_coordinator.py`, `src/xfinaudio/desktop/screens/my_playlists_screen.py` line 56.

**Evidence:**
- `grep` for `playlist_repository.create` and `last_recommendation` in `main_window.py` shows NO call to persist a recommendation as a playlist.
- `ReviewScreen` has NO "Save" or "Add to Playlists" button (only `back_requested`, `proceed_to_export_requested`, `track_remove_requested`, `track_play_requested`).
- `MyPlaylistsScreen` empty state (line 56) promises: "No saved playlists yet. Generate a playlist and click Save." - no such button exists in the generation flow.
- `PlaylistEditor` has a `save_button`, but it is only reachable from the My Playlists tab when editing an existing playlist.

**User-visible impact:** The user generates a 20-track recommendation, then cannot find it anywhere. Restarting the app loses it. The promise on the My Playlists screen is broken.

**Fix:** Add a "Save to My Playlists" action in `ReviewScreen` (or `BuildScreen`) that calls a new `PlaylistCoordinator.save_recommendation(name, track_paths)`.

---

### F2. [Medium] Rename button in MyPlaylistsScreen is a dead feature

**Location:** `src/xfinaudio/desktop/screens/my_playlists_screen.py` line 93-98, `src/xfinaudio/desktop/playlist_coordinator.py` line 80-87.

**Evidence:**
```python
def _on_rename_clicked(self) -> None:
    playlist_id = self.selected_playlist_id()
    if playlist_id is not None:
        # Simple inline rename via dialog would go here
        self.rename_requested.emit(playlist_id, "")
```
- The signal is emitted with an empty string.
- The coordinator handler `rename_playlist` early-returns on empty name.
- The comment admits the dialog was never built.

**User-visible impact:** Clicking "Rename" does nothing. Users assume the feature is broken.

**Fix:** Either remove the Rename button until a dialog is implemented, or add a `QInputDialog.getText` flow.

---

### F3. [Critical] Export crashes with FileNotFoundError on /tmp/xfinaudio-e2e-safe

**Location:** `src/xfinaudio/desktop/export_coordinator.py` line 384, `src/xfinaudio/quality/dj_readiness.py` line 120.

**Evidence:**
- Live error in app log:
  ```
  FileNotFoundError: [Errno 2] No such file or directory:
  '/tmp/xfinaudio-e2e-safe/XfinAudio%%Harmonic Journey%%20260614-185307 - ...dj-readiness.json'
  ```
- `write_readiness_sidecars` writes to `safe_folder` if provided, else `crate_path.parent`.
- `safe_folder` is None (user never configured a safe export folder), so fallback is `crate_path.parent` which does not exist.

**User-visible impact:** The Serato export fails with an unhandled `FileNotFoundError`. DJ readiness sidecar files never written.

**Fix:** Call `base.mkdir(parents=True, exist_ok=True)` before writing. Catch `OSError` in the export handler.

---

### F4. [Medium] `export_playlist` coordinator method is a no-op loop

**Location:** `src/xfinaudio/desktop/playlist_coordinator.py` line 110-116, `src/xfinaudio/desktop/screens/playlist_editor.py` line 98-100.

**Evidence:**
```python
def export_playlist(self, playlist_id: int) -> None:
    playlist = self._host._playlist_repository.get_by_id(playlist_id)
    if playlist is None:
        return
    self._host._playlist_editor.set_playlist(playlist)
```
- The method just loads the playlist into the editor.
- The editor's "Export to Serato" button emits `export_requested` connected back to `export_playlist` (line 62).
- Clicking Export on a saved playlist does NOT trigger an actual Serato export.

**Fix:** `PlaylistCoordinator.export_playlist` should delegate to the real export flow.

---

### F5. [Medium] Spectral jump warnings flood the Review UI

**Location:** `src/xfinaudio/recommendation/playlist_service.py` line 374-386.

**Evidence:**
```python
def _spectral_jump_warnings(tracks):
    warnings = []
    for left, right in zip(tracks, tracks[1:], strict=False):
        if left_color != right_color:
            warnings.append(f"Spectral shift: {left_color} -> {right_color}")
    return warnings
```
- A 20-track playlist with mixed colors produces many warnings.
- These feed into `recommendation.warnings` -> `needs_review` status.

**Fix:** Aggregate adjacent same-color shifts into a single summary.

---

### F6. [Low] Dual `tracks_table` between MainWindow and LibraryScreen

**Location:** `src/xfinaudio/desktop/main_window.py` line 475, `src/xfinaudio/desktop/screens/library_screen.py` line 141.

**Evidence:**
- `MainWindow` creates `tracks_table` with 11 columns; `LibraryScreen` creates one with 12.
- `MainWindow._build_layout` does not add `self.tracks_table` to any layout.
- `MainWindow._populate_track_table` populates the non-visible table.

**Fix:** Consolidate ownership in `LibraryScreen`.

---

### F7. [Low] Worklist empty state could be clearer

**Location:** `src/xfinaudio/desktop/screens/metadata_screen.py` line 137-149.

**Evidence:** When `state.scanned_records` is empty, combos still show "All / Complete / Incomplete".

**Fix:** Add explicit empty state label.

---

## 4. Inspection Meeting — Prioritized Findings

| # | Finding | Severity | Effort |
|---|---|---|---|
| F1 | Generated playlists never saved to My Playlists | Critical | Small |
| F3 | Export crashes with FileNotFoundError on /tmp | Critical | Tiny |
| F4 | Playlist "Export to Serato" is a no-op loop | Medium | Small |
| F2 | Rename button emits empty string | Medium | Tiny |
| F5 | Spectral jump warnings flood UI | Medium | Small |
| F6 | Dual tracks_table architecture | Low | Medium |
| F7 | Worklist empty state unclear | Low | Tiny |

---

## 5. Rework (Proposed Fixes)

**Critical fix 1 (F1):** Save generated playlist to My Playlists.
**Critical fix 2 (F3):** mkdir parents before writing readiness sidecars + friendly error.

---

## 6. Follow-up

Non-critical findings (F2, F4, F5, F6, F7) can be batched into a future "Playlist lifecycle" SDD change.

---

**Appendix A — Files reviewed:**
- `src/xfinaudio/desktop/main_window.py`
- `src/xfinaudio/desktop/export_coordinator.py`
- `src/xfinaudio/desktop/playlist_coordinator.py`
- `src/xfinaudio/desktop/screens/my_playlists_screen.py`
- `src/xfinaudio/desktop/screens/playlist_editor.py`
- `src/xfinaudio/desktop/screens/metadata_screen.py`
- `src/xfinaudio/desktop/metadata_view_model.py`
- `src/xfinaudio/quality/dj_readiness.py`
- `src/xfinaudio/recommendation/playlist_service.py`
- `src/xfinaudio/desktop/screens/library_screen.py`

**Appendix B — Live runtime errors observed:**
- 5x `FileNotFoundError` on `/tmp/xfinaudio-e2e-safe/...dj-readiness.json`.
