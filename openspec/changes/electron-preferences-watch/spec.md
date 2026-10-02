# Requirements

- Preview volume and watch preference persist in the isolated app data root across restart; no old profile or credential file is discovered/imported
- Versioned settings use immutable model updates; malformed settings are preserved by recovery and reported safely. Forged/unknown/path/secret fields and stale saves fail closed
- Preferences only control implemented behavior. Loudness/tag-writing/provider capabilities remain unavailable, with no service activation from defaults or restored settings
- Watchers receive only trusted-main authorized roots. Events are debounced and bound to the current lifecycle generation; queued old-root/paused/stopped/disposed events cannot publish changes
- Explicit completed scans publish clean state even if filesystem watching is unavailable. Partial/cancelled/failed scans cannot claim a fully clean library
- Cached startup state is explicitly restored/unverified; watch availability is separate from detected change state
- Manual rescan uses already authorized roots, preserves normal scan cancellation/incremental persistence and never accepts renderer file paths
- Disabling watching, starting a scan, backend failure and shutdown close watchers/timers without stale callbacks; re-enabling starts a fresh generation
- Dirty/unknown library status and rescan controls remain visible independently of operation progress and never hide core-disconnect errors
