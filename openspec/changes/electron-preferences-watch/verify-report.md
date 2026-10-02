# V6 cloud verification — 2026-10-01

## Verified result

- All 3,612 Python tests passed in 23 fresh whole-file batches through the supported aggregate release gate; combined coverage 94.34%, using the unchanged pyproject coverage floor.
- Aggregate exit 0. All 10 automated gates passed, including exact-collection/execution coverage integrity, type check, lint/format, release smoke, publication/source hygiene and PyInstaller check-only.
- Node/TypeScript verification: 189 tests passed, zero failures and zero skips. XFIN_PYTHON pointed to the independent Qt-free environment; all six real-core integration workflows ran.
- Focused settings/rescan/backend/protocol check: 45 passed. The full suite also verifies compatibility with original Qt settings/tests; no Qt dependency was added to the new executable/environment.

## Requirement evidence

- Bounded preference persistence/defaults/recovery/stale revision/symlink/oversize/invalid values: test_headless_preferences.py, existing settings-repository tests, library-host.test.mjs and renderer preference/controller/view/app tests.
- Authorized cumulative-root rescan, cancellation and unavailable-root failure: test_headless_rescan.py and real workflow.integration.test.mjs. Original/copy fixture audio hashes remain unchanged.
- Clean explicit scan independent of observer availability, dirty/unverified separation, generation tokens, timer invalidation, root replacement, pending close drainage: library-watch.test.mjs.
- Actual Linux Worker/fs.watch execution: native-watch.test.mjs covers nested changes, ignored app data, symlink/unavailable-tree refusal, new/replaced directory identities, and close waiting for worker termination.
- Main-only paths, bounded IPC preference fields, unavailable preference recovery retaining manual rescan, volume-only save without observer restart: library-host.test.mjs and security validation.
- Serialized startup, guarded initial player volume, explicit Save, combined editor/preferences dirty state, cancelled partial rescan, context/revision rejection of stale results and persistent offline status: renderer.preferences-app.test.mjs and renderer-player.test.mjs.

## RED → GREEN corrections

Preferences adapter, rescan behavior, native observer module, host integration and renderer integration each began with failing tests. Additional demonstrated failures covered a huge integer producing OverflowError, a replaced directory retaining an old inode watch, observation gaps incorrectly retaining clean state, unnecessary watcher restarts on volume-only saves, and preference-load failure hiding existing registered roots. Each now passes its regression.

## Evidence and limits

Aggregate log/report and individual batch collection/execution manifests are retained by the build task. Native V6 execution is pending and must use QA_PREFERENCES_WATCH_V6.md; actual cloud Electron remains blocked before app code by the host DBus environment. Node DOM and native filesystem-worker tests are not claimed as an Electron UI run.

No provider calls, loudness/tag writes, original audio modifications, live Serato writes, public push, merge, signed app or release occurred. The aggregate's inherited older “Mixed In Key audio QA: COMPLETED” field is not new Electron human/audible/stress acceptance. Bundled Python, full loudness and optional NaN/provider parity remain separate migration work.
