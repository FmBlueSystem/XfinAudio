# Observable requirements
- R1 GIVEN valid settings WHEN a write, fsync or replace fails THEN the prior complete file remains readable and temporary files are removed.
- R2 GIVEN malformed or unsupported settings WHEN desktop startup loads them THEN original bytes are preserved in a unique recovery file and defaults load with a visible recovery diagnostic. If preservation fails, loading reports a typed error without replacing the source.
- R3 GIVEN settings cannot be saved WHEN the user applies settings THEN the UI explains the failure and the last valid in-memory settings remain active.
- R4 GIVEN an existing playlist WHEN it is deleted THEN its child references disappear and SQLite foreign_key_check is empty.
- R5 GIVEN a legacy DB with orphan references WHEN opened THEN only orphans are removed; valid playlists, ordering and references remain.
- R6 GIVEN repeated successful or failed repository operations WHEN each operation ends THEN its SQLite connection is closed and writes commit or roll back normally.
- R7 GIVEN invalid-settings recovery WHEN persisted tracks restore THEN automatic loudness write-back stays disabled until the user reviews/re-enables it. Normal fresh settings defaults remain unchanged.
- R8 GIVEN primary persistence and temporary cleanup both fail THEN callers receive the typed primary settings error; cleanup must never mask it.
