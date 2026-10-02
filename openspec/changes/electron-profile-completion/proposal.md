# Proposal: read-only profile completion parity

Restore the original spectral, danceability and edge-profile completion chain in the Qt-free application. Metadata remains immediately available; the Electron client starts a separately cancellable completion job after successful scan/rescan and offers an explicit retry. Reuse the original analyzers, model versions, repository cache/persistence, hard gates and scoring. Restore the original spectral-cohesion preference (default 0.5).

Out of scope: new DSP, tonal extraction, source/tag/audio writes, automatic loudness, providers, live Serato writes, release/push/merge. Silent/unreadable excerpts stay honestly unavailable. Rollback is the preserved legacy Qt application or disabling the new client scheduling while keeping metadata scans.

Risks: expensive cold librosa imports, cancellation cannot interrupt a currently decoding file, stale file/cache identities, persistence failure, and renderer race with subsequent work. Bound the pool to at most two workers and stage sequentially; revalidate identities before caching; use the existing exclusive job lifecycle.

Review chain (explicit >400-line plan): (1) Qt-neutral completion/cache/status + unit tests, (2) preferences and existing scoring parameter plumbing + tests, (3) host/renderer scheduling and status + tests, (4) hash-locked Qt-free runtime dependencies + integration/packaging evidence. Each review slice targets <=400 changed production lines and separately reviewable tests.
