# Architecture and safety

`legacy_source.py` takes only a native-selected absolute directory, rejects every symlink path component, uses bounded O_NOFOLLOW reads and hashes stable snapshots. Presence of SQLite -wal/-shm/-journal means refusal with close/checkpoint guidance; immutable in-memory deserialization avoids source SQLite lock/sidecar writes. Only current known schemas are accepted. No source connections or track-path stat calls occur.

`legacy_validation.py` rebuilds independent staged databases through existing repository schema/models and copies only validated known rows, preserving file identity for future separately authorized scanning. Settings are positive-allowlisted volume and spectral cohesion; watch, loudness, AI and Serato are disabled. Source settings are never copied wholesale.

`legacy_import.py` owns one short-lived preview; native host owns the matching grant. Source snapshots are revalidated at apply. A durable confined journal records backups before replacement. Startup recovery hook runs before repository construction. Backups and workspaces are never automatically deleted. Successful import reports restartRequired and blocks further commands in the old backend lifetime.

Explicit bounds: 256 MiB per database, 256 KiB settings, 100,000 tracks, 5,000 playlists, 250,000 playlist references, 20 preview names, 200 characters/name. No audio or credential path accesses, no provider/network, no live Serato. Tests only synthetic fixture directories under workspace.

Final review slices are independently bounded: source helpers (123 lines); schema reconstruction (147); transactional coordinator/recovery (323); Python regression companion (383); native host plus native tests (72); renderer/controller/view plus renderer tests (54); SDD documents; shared integration reviewed by its owner. Review each companion slice alongside the behavior it exercises; never combine these as one unreviewed >400-line patch.

The final filesystem implementation uses `serato_safety.open_directory` for ancestor-by-ancestor O_NOFOLLOW and dir_fd leaf operations. Source snapshots hold the selected descriptor across both bounded reads and recheck lineage. Staging databases are built with the existing repository schema/model helpers in memory. Native authority is `legacy.apply {previewId, confirmed:true}`; renderer cannot send confirmed. `recover_legacy_import` returns whether it found a completed commit, preventing a final-journal failure from being mislabeled a rollback. Root grants are rechecked during publication and never imported.
