# Persistent preferences and safe library-change lifecycle

Restore useful app-owned preferences and library-change indications without Qt. Reuse versioned AppSettings/SettingsRepository for preview volume and an additive watch preference. Use Node's native filesystem watch through a testable lifecycle owner in Electron main; no new dependency, network listener, OS setting or background daemon.

Library scans remain read-only. Loudness/provider runtime composition is explicitly outside this slice: their legacy settings must not silently activate tag/comment writing or provider calls. The preferences screen discloses unavailable capabilities rather than offering inert controls. Only Spanish UI is available in this preview.

Chained review plan, each publication patchset capped at400 added+removed lines: bounded settings adapter and compatibility tests; authorized-root/rescan backend; watcher generation/debounce/error state and tests; main/preload integration; preferences/status renderer; end-to-end/native fixture verification. Split units further before publication as necessary.
