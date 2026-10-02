# Design

Add LibrarySettings.watch_for_changes with a backward-compatible true default. A headless preferences adapter exposes only revision, previewVolume, watchLibrary, safe last-library labels/recovery warning and explicit runtime capabilities. It reuses immutable AppSettings and SettingsRepository, bounds the settings file and rejects symlinks. Updates compare the loaded file revision and preserve unrelated settings; no AI env path or key is returned.

Main-only library.roots returns authorized canonical roots for watching. Renderer gets labels/counts and no paths. library.rescan revisits registered roots through the existing scanner, honoring its cancellation token and partial persistence. Main coordinates pause/completion around scans; clean publication does not depend on watcher success.

A dependency-injected Node watch owner records roots, dirty/unverified state, generation and debounce timer. Raw events/error handlers close over a generation token. Stop/pause/root replacement invalidates tokens and clears timers before closing resources. The app-owned data directory is ignored to avoid self-generated profile/database notifications.

Preload exposes bounded preference/rescan/status APIs and a status subscription. Renderer settings edits are explicit save/cancel with stale-revision recovery; the existing player volume is restored without autoplay. Native fixture validation covers queued events, failed watcher startup, scan publication and restart persistence; no audio writes.

Native observation uses a dedicated Node Worker and per-directory non-recursive fs.watch handles. Directory enumeration, canonical/inode checks and handle replacement stay off the Electron main thread. Symlink-containing trees fail closed rather than following targets. Bounds are 64 roots, 50,000 entries and 4,096 directories per root, with a 128 MB worker heap. The worker coalesces root notifications for 75 ms; the generation owner debounces them for 350 ms. New/replaced directory identities get fresh handles. Worker termination is awaited; inactive generations cannot publish late callbacks.

Volume-only saves do not restart the observer. Explicit observer replacement marks its observation gap unverified; completed explicit scans independently clear only completed roots. Preference-load failure retains registered roots for manual rescan. The renderer ORs preference/editor dirty state, treats footer changes as session-only, and guards initial persisted volume against user interaction before bootstrap completes.
