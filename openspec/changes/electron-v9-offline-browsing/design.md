# Design

`headless/library_browse.py` wraps `LibraryQuery`, `parse_library_query`, `duplicate_group_key`, and `duplicate_representative_sort_key`. It never imports desktop/Qt. Sorts operate on a private view; public results use existing SHA-256 track IDs.

`application/playlist_recovery.py` archives exact playlist JSON in an app-owned SQLite table, compares all original fields under BEGIN IMMEDIATE, removes active rows in the same transaction, and restores under a new ID once. Backups are retained with restored identity for auditability. No audio files are accessed.

`headless/saved_browser.py` exposes search/compare and one active revision-bound delete preview, plus archived summaries/recovery. The original search/compare helpers are reused. Commit requires trusted-main confirmation; the renderer has no raw backend channel.

`src/offline-host.ts` owns native confirmation and awaits recovery-safe commit. `src/offline-security.ts` provides strict bridge fields/shape validation. `renderer/offline-browse.ts` owns provider-independent controls and stale-response guards. Shared main/preload/app/backend integration composes these dedicated modules while preserving the profile lifecycle.
