Implementation starting with tests; no audio writes have run.

## 2026-10-01 implementation checkpoint

- Original three loudness settings and the exact LoudnessBand now reach both real candidate planners and the domain Prep builder. Shared settings revisions/locks/recovery preserve unrelated preferences.
- Real FFmpeg/FLAC subprocess test passes with finite measurement, exact original-byte backup, decoded PCM SHA256 invariance and cache replay. Actual descriptor-based FLAC/WAV/AAC-M4A/ALAC-M4A writes also pass; unchanged repeated tags create no new backups.
- Source identity/lineage, stale scanner identity, symlink/path changes, post-backup replacement and incomplete profiles are tested. Original-byte backups have exclusive per-file recovery manifests, synced before a changed save.
- Native main confirmation, cancellation before late dialog acceptance, in-flight commit drainage, bounded IPC and fixed backup-directory reveal are tested. Backend receipts retain counts/warnings after post-write cache/status failure.
- A real-shaped server lock/commit-progress deadlock was reproduced and fixed: mark cancellation under publication lock, drain outside it, then join. Hook retirement/invocation is serialized and exactly once; a failed hook cannot skip other drains/shutdown.
- Full Python source/config frozen and supported sharded aggregate started at 17:28 UTC. Final Node validation follows the last recovery UI affordance.
