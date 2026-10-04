# Feature: recover and bound the Electron library boot

## Goal and evidence

The owner opened the personal QA DMG in their existing account and reported an empty Library (not merely a missing Tonalidad column). The app and bundled core were gracefully stopped before investigation. Immutable read-only SQLite checks found 10,391 tracks, 10,383 with a Camelot key, and all with BPM, energy, duration, audio format and bitrate; the sole configured root lexically contains all rows and the sampled audio files exist. The **packaged core** independently returned all 10,391 rows through both `library.list` and the alternative neutral `library.query` in ~4.8 seconds per request from a private diagnostic copy. No scanner or tag mutation is justified.

The source UI performs a synchronous full-library DOM render and full-size track selectors. A one-shot mocked 10,391-row renderer benchmark completed, but its DOM is not real Electron: the cause of the owner's empty screen remains unproven. Separately, the library bootstrap permanently leaves an empty table after any request/apply failure and immediately hides its error with idle-work status. Treat recovery and bounded rendering as testable defects, **not** proof that the installed artifact is already fixed.

## Constraints

- Existing personal account only; never mutate audio, Serato DB V2, or the live XfinAudio profile for tests.
- Keep copied diagnostic profile private; no titles, paths or full response in repo/test output. Source baseline artifact is commit `6c045f3`, while the current feature branch initially points to `9107b9e` with documentation-only intervening commits.
- Scope to renderer/transport behavior and synthetic test fixtures; no public distribution, push, PR, merge or release.
- Observe strict RED → GREEN, required `openspec/changes/library-boot-recovery/` artifacts, ≤400 changed diff lines per reviewable work unit, and Conventional Commit(s). Full gate and Electron suite precede any replacement app build. A source test never proves actual app launch.

## Work units

1. [x] Specify and test library bootstrap failure recovery. A persistent `#library-recovery` panel retains the error through idle work, and its gated retry calls only `listLibrary` without scanning or writing the profile. SDD artifacts, fake-DOM tests and behavior share commit `b3b683a9d476055bddce085d4ba60056f6813acd` (307 changed lines). RED: 3/3 expected failures; GREEN: 3/3 passed; 205 focused renderer/library tests passed with zero skips. Independent verifier reran build and 9 focused tests (9 passed, zero skips) and reviewed gate/retry paths. Native ASSESS was temporarily unassessable because this parent-owned task document remained untracked; reassess the normalized candidate. Real Electron visibility and the original empty-screen cause remain unverified.
2. [x] Bound first paint to 200 rows with a visible 200-of-total note and load-more control; retain all matches for search and sort, and defer full (untruncated) Prep option lists until Prep is used. Commit `e2df9c8149afc2f0cbbf4e1f49ee8d7966e22263` (203 diff lines). RED 2 of 27 tests failed as expected (650 rendered rows and eager options); GREEN 27/27 passed. `npm run build` passed, independent full release gate passed (4205 Python tests, 94.45% coverage, pyright/ruff/source checks clean) and Qt-free Electron wrapper passed 434/434 with zero skips. No real-DOM/owner-app first paint was observed; work unit 3 remains open.
3. [ ] Build a new, sealed personal QA artifact from the verified updated source only if the owner wants replacement; manually verify first launch against the real account, count and Tonalidad, then listening/library/Serato with separate safety checks. Current DMG is tied to `6c045f3` and must not be presented as containing this fix. Evidence: pending; cannot claim real UI acceptance from mocks.

## Diagnostic privacy

A mode-700 temporary diagnostic directory containing copies of profile databases and the full core response remains at `/Users/freddymolina/Desktop/XfinAudio-personal-qa-6c045f3/.diag_20261003_231410/` after delegated cleanup was blocked. Do not publish or commit it. Remove only this verified, newly created scratch with explicit authorization or a safe authorized cleanup path.
