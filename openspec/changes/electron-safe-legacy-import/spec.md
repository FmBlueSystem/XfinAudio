# Observable requirements

- Given no selected directory, import never discovers or reads the user's legacy HOME path.
- Given an exact native-selected directory and closed/checkpointed old app, preview reads only xfinaudio.sqlite3, playlists.db, settings.json and checks known sidecars. Unknown files and audio are never opened.
- Given symlinked, corrupt, unsupported, oversized, changing, or journal/WAL-dependent files, preview fails safely and writes no source bytes.
- Given a populated destination or existing preferences/grants, import refuses without overwriting.
- Given valid selected data, preview reports bounded counts and safe settings with opaque identity; no source path, credentials, or audio metadata is returned.
- Given cancelled native confirmation, no import occurs. A changed source/destination invalidates approval.
- Given successful confirmation, import preserves playlists/order and cache without authorizing roots or enabling providers/background writes, retains backups and restarts before further workflows.
- Given partial commit or crash, startup restores the full previous profile before repositories open, retaining all backups; failed recovery blocks startup.
- Given an aliased application-data root (including a symlink ancestor), standalone backend startup rejects before opening repositories, creating grants or running recovery writes. Electron storage supplies the canonical real path. This early rejection supersedes the former test-only behavior of starting an aliased backend and refusing only later loudness writes.
