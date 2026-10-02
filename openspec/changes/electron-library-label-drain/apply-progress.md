# Apply progress

2026-10-02: proposal, specification, design and tasks initialized before behavior edits. Baseline is the verified R3 source seal 85bdd7e9989f2a6cf57035e68cfff7dbafe861c67aeff28a44b4cf09f7011f84. RED pending. Prior snapshots remain immutable.

RED: baseline build passed; app preference tests ran 15 cases, 13 passed and two expected overlap failures observed (read count remained 2 instead of 3). The failure-without-new-event regression already passes and bounds the intended correction. Evidence is external at /workspace/shared/xfinaudio-v17-r4-evidence/label-drain-red.log.

GREEN implementation: only the existing label-refresh promise completion triggers a guarded queued-label drain. A read consumes its flag before launch, so failure alone cannot schedule another read.

Focused GREEN: TypeScript/assets build passed, then preferences controller, app preferences, renderer-controller and profile scheduling suites passed all 48 tests, zero skips. New tests prove successful/failed overlap drains once, bursts coalesce, stale returned settings revisions/values do not overwrite drafts, footer playback remains unchanged, and failure without a new notification stops until explicit refresh. No further refactor was needed. Source is prepared for freeze; patch and SHA256 manifest are external.
