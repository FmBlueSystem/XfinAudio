# Host and renderer review slices

Scope: Electron main/preload allowlist, cancellable profile completion controller, library summary, and independently revisioned spectral-cohesion card in Preferences. Keep metadata rows available as soon as scan completes. Do not add color labels or track DTO fields, paths/commands, provider traffic, loudness calls, autoplay, or source writes.

## Scenarios and architecture

1. Successful scan/rescan queues exactly one completion after publishing metadata; cancelled/failed scans do not queue it. Startup only reads status. A retry is explicit.
2. Completion is exclusive and stays busy until cancellation drains. Repeated scans/retries cannot overlap. Close cancels and awaits completion before core shutdown.
3. Stage progress contains only known stage and bounded integer counts; unknown fields and text are dropped. Partial/cancelled/unavailable summaries stay truthful and retryable.
4. Completion and cohesion save invalidate dependent Prep, Live, editor previews, Serato previews, and AI suggestions. Watch changes cancel stale completion; no late result replaces the newer library context. Dirty editor drafts remain preserved.
5. Cohesion edits are local until explicit save; default 0.5 comes from core. Navigation and close protect dirty state. Stale revision preserves drafts and requires discard then refresh. No automatic save/retry.
6. No scan/startup/completion path starts playback, loudness writes or provider calls.

Review chain: separate host/IPC + lifecycle tests; renderer completion + integration tests; Preferences card + controller tests. Each production slice targets <=400 lines, following the proposal's explicitly approved chained review.

## TDD execution

- RED recorded: `/tmp/xfin-profile-host-red.log` (5 missing behaviors), `/tmp/xfin-profile-renderer-red.log` (5 missing flows), `/tmp/xfin-profiles-watch-red.log` (paused stale watcher regression) before each production change
- GREEN: host lifecycle/allowlist, renderer metadata-first auto-completion, independent revisioned cohesion card; 10 initial focused tests passed
- REFACTOR: safe aggregate DTO validation, stage-only progress projection, exclusive completion drain; successful rescan clears old paused watcher dirtiness only when latest library status is no longer changed
- VERIFY: strict TypeScript build passed; initial full Node suite passed 288 tests with 8 real-core tests skipped pending new dependency environment. Added two interruption/watch regression cases; rerunning focused suite. Actual synthetic core workflow remains pending dependency environment; full aggregate Python verification is recorded separately

## Verified profile handoff

- Strict TypeScript build: PASS (main + renderer)
- Focused Node contract/lifecycle/app tests: 12/12 PASS
- Full Node suite before the two additional watcher/failed-scan regressions: 288 PASS, 8 real-core integration tests SKIPPED without XFIN_PYTHON; this is not the final aggregate gate
- Actual Qt-free bridge test using `.venv/bin/python`: PASS, 28.4 s, no skips. Generates three disposable 70-second audible FLACs, cancels/drains an initial profile pass, completes all three original profile classes, verifies both Same Color strategies, revision-bound cohesion conflict handling, restart/cache persistence, unchanged source SHA256 and nanosecond mtime
- Tests: `desktop-electron/tests/profiles-host.test.mjs`, `profiles.test.mjs`, `renderer.profiles-app.test.mjs`, `profiles.integration.test.mjs`
- Commands: `npm run build --prefix desktop-electron`; `node --test desktop-electron/tests/profiles-host.test.mjs desktop-electron/tests/profiles.test.mjs desktop-electron/tests/renderer.profiles-app.test.mjs`; `XFIN_PYTHON="$PWD/.venv/bin/python" node --test desktop-electron/tests/profiles.integration.test.mjs`
- No release, push, provider calls, real-library changes, source audio/tag writes, autoplay, or live Serato writes performed by this slice

## DTO correction during shared integration

Safety review identified that completion's `completeCount`/`incompleteCount` preserve metadata-library meanings, while `status.readyCount`/`pendingCount` represent profile completeness. Added a failing renderer regression for tagged tracks with unavailable profiles and profiled tracks with missing tags, then changed result validation to compare metadata counts against the returned metadata rows independently. Both cases now pass; status summaries remain driven solely by profile aggregate counts. The initial cancellation/unavailable mock fixtures were corrected to carry metadata counts.

## Final shared-boundary checkpoint

All restored host/render integrations are now composed: offline browse/saved recovery, generated review evidence and edits, persisted Prep controls, metadata/Library worklists through existing Serato export, and explicit safe legacy import with restart isolation. Final shared renderer/boundary regression command uses `renderer*.test.mjs` plus profiles, restored-wiring and legacy host/controller tests; all pass (see the matching final aggregate for the complete all-feature/Python gate). Narrow Library toolbar now wraps the additional scoped-export control. This checkpoint does not claim native screenshot coverage or a complete release gate; those final checks are recorded separately.
