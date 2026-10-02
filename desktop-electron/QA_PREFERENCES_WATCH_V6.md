# V6 native fixture verification: preferences and read-only library observation

Use a separate materialized V6 checkout, Qt-free Python interpreter, and explicit isolated XFIN_DATA_DIR. Keep the V5 checkout and its data frozen. Use synthetic tracks and authorized copies only; never touch original audio, live Serato data, old app profiles or system settings. All new behavior is read-only toward music. Existing loudness/provider settings do not start those services in this preview.

## Automated prerequisites

Run `XFIN_PYTHON=<headless-python> npm test` from desktop-electron. The suite includes real Node Worker/fs.watch execution and real Python subprocess workflows. All tests must run with no opt-in skips. Source dependencies are unchanged and locked. Do not disable Electron sandboxing. Record platform, source SHA256, Node/Electron/Python versions and test output.

## Native application matrix

1. Launch with isolated XFIN_DATA_DIR. Assert all Chromium paths are still beneath it, sandbox/context isolation enabled and no PySide6 import. Scan two temporary music folders. Status must show clean after completed explicit scanning; observer state is separately active/unavailable/disabled.
2. Open Preferences. Initial volume is 70%; set 23% and disable library observation, then Save. Confirm player volume updates without autoplay. Restart: settings and two library labels persist. Footer volume changes are session-only. Editing preferences without Save must not apply to audio or the settings file.
3. With unsaved preferences plus an unsaved playlist edit, discard only one. Native Close must still warn for the other. Cancel must preserve a usable core, drafts and observer. Explicitly discard both before a clean close.
4. Enable observation and Save. Wait for active or a truthful unavailable state. Restarted observation shows restored/unverified until an explicit rescan. Use a new disposable marker file inside a copied/synthetic root: a burst of changes coalesces to changed. No automatic rescan or audio mutation occurs.
5. Rescan registered roots using the status control. No folder path is accepted from the renderer. Completed scan publishes clean; cancelled/failed scan must not falsely clear unknown/changed state. Delete only a disposable copied synthetic track and verify existing missing-file behavior, then restore the fixture.
6. Create a temporary nested folder, then replace it with another directory at the same path. Notifications must continue for the replacement. Changes under the application-owned data directory must not mark the music library changed.
7. Disable observation; late events must not revive changed/active status. Re-enable, rescan, then trigger a change while Prep is pending and verify stale Prep/Live/Serato eligibility cannot be revived by the late result. Dirty editor text survives, but old edit/export previews are invalidated.
8. Using separate disposable roots, test a directory containing a symlink and an unavailable root. Observation fails visibly while explicit scan publication remains independently clean when scanning itself succeeds. Never follow the symlink into an external music tree.
9. Modify only the isolated settings file between Preferences load and Save. Stale save must preserve the draft and explain refresh/discard; it cannot overwrite the newer settings. A corrupt settings fixture is preserved by the existing recovery flow and write-capable services remain off. A symlink/oversized settings file is refused.
10. Close while observation setup/events are pending. Verify all owned worker threads and Python child processes exit. Repeated close must coalesce. Core-disconnect status must remain visible and Live must remain unavailable even when a later watcher shutdown status arrives.
11. Re-run baseline Prep/review/save/restart/open/editor, muted FLAC pause/seek/switch, Live and temporary Serato smoke. Compare all original/copy/Serato sentinel hashes and record zero owned processes after exit.

## Intentional bounds and limitations

The native worker watches directories individually without following links. A root containing a symlink, more than 50,000 entries or 4,096 directories is reported unavailable; at most 64 roots are observed. Watcher errors, unsupported mounts and unavailable permissions also require explicit manual rescan. Bounds apply to observation, not a fabricated successful scan. OS notifications are advisory and are not a guarantee that a library cannot change between scan and use; existing source validation remains authoritative for sensitive operations.

No actual provider calls or loudness/tag writes; no live Serato import; no installer/bundled-Python distribution yet. Controlled dialog responses and muted programmatic playback do not establish human, audible, prolonged or removable-filesystem acceptance.
