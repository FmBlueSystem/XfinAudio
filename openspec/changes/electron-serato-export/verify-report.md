# V4 verification checkpoint — 2026-10-01

## Verified in Linux cloud

- All 3,538 Python tests passed in 23 fresh-process coverage batches on the final Python source; combined coverage 94.29%, using the configured floor without overrides
- Full Pyright: 0 errors/warnings; locked Ruff 0.15.15 lint and format pass; git diff whitespace check passes
- All 122 Node tests pass, no skips, with four actual Qt-free Python subprocess integrations
- Real Serato fixture flow: scan copies, real Prep, exact saved order, preview without writes, cancelled confirmation, confirmed crate, duplicate receipt without another write, overwrite backup/readback, stale-source rejection, unchanged audio/database sentinels
- Host tests: opaque-only IPC, native destination/confirmation separation, rejected extra path/confirmed/bytes/readiness fields, cancelled dialogs, duplicate clicks, close during confirmation, noncancellable publication drainage and verified receipt-only reveal
- Renderer tests: review/saved entry, strict preview→commit, source/name/destination invalidation, new variant invalidation, dirty-editor protection, receipts across navigation and safe Spanish errors
- Filesystem tests: source/destination/leaf/ancestor changes, exclusive publication, backup collisions, readback recovery, preservation of concurrent arrivals at overwrite and rollback cleanup, retained recovery copies, 500-reference/16 MiB bounds
- Source handoff tests: reproducible regular-file-only archive, exclusion of dependency symlinks/generated trees, rejection of unexpected links and sensitive configuration
- Release readiness smoke, source-package hygiene and PyInstaller check-only pass. Source package check reused the existing cache offline; no new Qt installation or root build/dist directory

The initial in-progress full run caught the new rollback-race RED test. That run is not the final gate. The corrected Python snapshot was rerun completely; all final batches/checks returned zero. Renderer-only variant invalidation then passed the complete 122-test Node suite. No Python code changed during the final full run.

## Remaining native checks and limits

Native macOS V4 testing is pending; use `desktop-electron/QA_SERATO_V4.md` and disposable `_Serato_` fixtures only. Linux exclusive rename is exercised; Darwin ABI/flags have mocked tests, not a native filesystem claim. No live Serato import, real-library write, audible playback, human acceptance or long-library stress is claimed.

The original aggregate release command previously exited 137 with accumulated legacy Qt process resources. Fresh-process verification preserves all tests/coverage but does not relabel that command as passed. No signed package, DMG, public push, merge or release was produced. A tested explicit sharded aggregate gate remains required before release.

Overwrites briefly capture the prior public filename before exclusive publication; backup remains throughout. Shutdown may exceed the normal six-second bridge grace period while a confirmed publication safely drains. Recovery conflicts retain copies for inspection rather than overwriting another writer's file.
