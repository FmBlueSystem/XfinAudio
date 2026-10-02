# Apply progress

SDD initialized before production edits from source archive v14; all edits remain isolated. Chained review slices are declared in proposal.md.

- Metadata RED: 10 failures proved untagged stream omission, absent model/DTO fields and missing migration. GREEN: six real generated audio formats plus MP3 CBR/VBR, read-only hash/mtime checks, regular and display repository reads, restart, absent/invalid metadata and misleading extension. No extension-based encoding guesses.
- Global sorting RED: 11 Python failures and new main-process whitelist rejection. GREEN: all nine columns, numeric Camelot and bitrate order, nulls last both directions, path-stable ties and 650-record query. Source recommendation records remain unchanged.
- Whole-app RED: missing displayed facts, inaccessible/nonexistent sort buttons, unavailable global header behavior and stale indication. GREEN: every actual data header is a native button with aria-sort and arrows; index and listening controls remain unsorted. Title and artist are independent columns; genre uses its existing sort capability.
- Applied local filters and sort state have one owner. Headers preserve unsaved filter drafts, applied duplicate suppression, search/status/AI filters, preview and Prep selection. Failed/stale requests retain the last valid indication; current accepted responses alone restore keyboard focus. The initial scan-order option is an informational disabled option rather than an action that would silently choose a different order.
- Additional migration RED found DDL could survive interruption; explicit transaction now rolls back columns and user_version. Copied populated old-state ordinary rescan fills all properties without audio identity changes or source-DB writes.
- Legacy schema-5/6/migrated-7 imports were RED and are now GREEN. Definition allowlists remain strict, unknown extra columns reject, and named inserts handle physical column-order differences.
- No new dependencies, user audio/provider calls, user data import, live Serato writes, package build, publication or redesign. Native QA and the aggregate integration release gate remain with the coordinator.
