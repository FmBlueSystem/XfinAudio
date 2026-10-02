# Verification

## Outcome

The queued folder-label refresh now drains after the preferences controller clears pending. Completion checks the existing queue once; a failed read without a newer root notification cannot create another attempt.

## Fresh evidence on V17-r4

- RED: baseline build passed; 15 app preference tests ran, 13 passed and the two overlap cases failed with reads 2 rather than expected 3.
- GREEN: build passed; 48 focused tests passed, zero failed, cancelled, skipped or todo.
- Commands: `npm --prefix desktop-electron run build`; `node --test desktop-electron/tests/renderer.preferences-app.test.mjs desktop-electron/tests/preferences.test.mjs desktop-electron/tests/renderer-controller.test.mjs desktop-electron/tests/renderer.profiles-app.test.mjs`.
- External evidence directory: `/workspace/shared/xfinaudio-v17-r4-evidence/`; logs `baseline-build.log`, `label-drain-red.log`, `label-drain-build.log`, `label-drain-green.log`.

## Requirements

- Success overlap: two newer root-count notifications during the delayed read cause exactly one subsequent read and show the latest labels.
- Failure overlap: the same newer notifications still receive one read after the old read fails.
- Failure without a newer event: read count remains bounded while idle; explicit Refresh still works.
- Preservation: the latest label snapshot does not replace dirty volume/watch values or their original save revision; footer volume and paused state remain intact; route title remains and the main landmark receives no new focus call. The explicit save at the end of the test verifies the preserved revision/value payload.

## Limits and final gate ownership

These are isolated renderer/controller tests using the existing fake DOM; they prove API scheduling and modeled state, not native geometry or physical keyboard focus. The parent separately reports R3's five incremental native cases passed. This correction changes no visual layout or engines. No new native matrix, full Node wrapper or Python gate ran in this work slice. The parent will run and retain authoritative final full-gate evidence against the frozen exact source outside the checkout. This report intentionally remains a truthful focused checkpoint and need not be edited for later gate counts.

One bounded review unit includes the renderer scheduler, three generated test cases and these seven SDD artifacts, below the 400-line budget. The external patch/hash manifest records the exact size and final file hashes.
