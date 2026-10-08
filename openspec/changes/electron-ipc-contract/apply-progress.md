# Apply progress

2026-10-03 (artifacts-only session, branch `feat/electron-ipc-contract`): Proposal, spec, design
and tasks are complete. **Apply has not started and verify is pending.** No production code, test,
`package.json`, lockfile, or other change artifact was created or modified in this session.

## Scope boundary observed

Only `openspec/changes/electron-ipc-contract/*` was written. `openspec/changes/electron-qt-free/`
and `openspec/changes/electron-publication-readiness/` remain untouched; both are referenced rather
than overwritten. The pre-existing untracked `odd/tasks/electron-installable-release.md` was left
as found. Nothing was staged, committed, pushed, or published.

## Verification of the parent's premise

The stated premise ("parity of `validateRequest` allowed methods with the `main.ts` switch and
`preload.ts` exposed methods; currently 60 match") was re-derived from source, expanding the two
spread tables that a naive enumeration misses:

- `desktop-electron/src/security.ts:35` literal `fields` keys: 48 (including `cancelCurrent`)
- `desktop-electron/src/offline-security.ts:2` `OFFLINE_FIELDS`: 6
- `desktop-electron/src/review-security.ts:3` `REVIEW_CONTROL_FIELDS`: 6
- effective allowlist A: 60; `action()` switch cases S (`main.ts:109-181`): 60; preload dispatch
  actions P (`preload.ts:3-42`): 60; all three sets are equal in both directions.

Corrections to the premise worth recording:

1. The parity is three-way **and already exact** (A = S = P = 60). The security gap is not the
   counts; it is that the parity is untested and that the two spread tables are invisible to a
   straightforward key scan. An independent extraction that ignores the spreads will wrongly
   report 12 switch actions as "missing from `validateRequest`"
   (`reviewDetails`, `reviewCompare`, `reviewRemove`, `reviewReorder`, `prepSettings`,
   `savePrepSettings`, `queryLibrary`, `searchPlaylists`, `comparePlaylists`, `deletePlaylist`,
   `listDeletedPlaylists`, `restorePlaylist`); those 12 arrive through the spreads and are
   validated by `validateReviewControlRequest`/`validateOfflineRequest`.
2. The actual fail-open is the missing `default:` arm at the end of the `action()` switch
   (`main.ts:109-181`): an allowlisted-but-undispatched action would resolve `undefined`
   silently. It is latent today because A = S, and it is the RED target of task 2.
3. `preload.ts` exposes 60 dispatch actions plus 2 subscription helpers (`onLibraryStatus`,
   `onProgress`), which are channels and not part of the parity contract.

## Evidence commands used (read-only)

No verification command from the spec has been run for this change yet. The parity figures above
came from read-only enumeration of the three source files; they are proposal-phase evidence, not
test evidence. `verify-report.md` records that no test result exists yet.

## Deviations and risks

- Strict TDD requires an observed RED before the production change. The production change is a
  single `default` arm; its RED is the structural guard assertion in the new test file, which
  fails before the arm exists. This is a source-level RED, not a behavioral one — justified in
  `design.md` (rejected alternative) and disclosed in `verify-report.md`.
- Apply-phase edit surfaces (`desktop-electron/src/main.ts` and the new test file) are outside this
  session's allowed write set by instruction; the parent owns authorizing them for the next unit.

## Slice B — apply under strict TDD (2026-10-03)

Branch `feat/electron-ipc-contract`, after docs-only commit `2422ffc`. Production diff is one line;
the guard test applied at 63 readable lines with the R1 assertion at line 42 (at the observed RED it
was a 22-line draft with the R1 assertion at line 14). No Python, preload, security, renderer,
dependency, or lockfile change.

### RED (observed, before the production change)

- Command: `cd desktop-electron && npm run build && node --test tests/ipc-contract.test.mjs`
- Result: build exit `0`; test exit `1`; `# pass 0`, `# fail 1`.
- Exact failure: `AssertionError: R1: action() must end in a throwing default arm` at
  `tests/ipc-contract.test.mjs:14` — the then-22-line draft's line for that assertion (historical
  location; the assertion now sits at `tests/ipc-contract.test.mjs:42` in the 63-line file) — from
  `assert.match(dispatch, /default:\s*throw new Error\('Unsupported action'\)/)`.
  The `action()` switch slice ended at the `cancelCurrent` case with no `default:` arm.

### GREEN (observed, after the production change)

- Change: `desktop-electron/src/main.ts` gained the final arm
  `default:throw new Error('Unsupported action');` immediately after the `cancelCurrent` case.
- Command: `cd desktop-electron && npm run build && node --test tests/ipc-contract.test.mjs`
- Result: build exit `0`; test exit `0`; `# pass 1`, `# fail 0`.

### TRIANGULATE (observed)

- Real end-to-end drift: temporarily removed the `case 'listLibrary':` line from `main.ts`, ran
  `node --test tests/ipc-contract.test.mjs` → exit `1`, `# pass 0`, `# fail 1` (R2 `deepEqual`), then
  applied the exact inverse edit; `git diff -- desktop-electron/src/main.ts` then showed only the
  one-line `default` arm.
- In-memory drift through the exact guard regexes (no file writes; the disallowed `security.ts` and
  `preload.ts` were never mutated on disk): baseline `A=60 S=60 P=60 A==S==P true`; removed
  allowlist key → `A==S false`; preload key/method mismatch → key-equals-method `false`; removed
  switch case → `A==S false`.

### Verified commands (observed)

- `cd desktop-electron && npm run build && node --test tests/ipc-contract.test.mjs` → exit `0`,
  `# tests 1 / # pass 1 / # fail 0`.
- `cd desktop-electron && npm test` → exit `0`, `# tests 429 / # pass 418 / # fail 0 / # skipped 11`.
  The 11 skips are the pre-existing environment-dependent integration tests, not new.
- `XFIN_PYTHON=<qt-free interpreter> python scripts/electron_ci_check.py` → exit `0`.
  `.release-evidence/electron-test-report.json` reports `status: passed`, `returnCode: 0`,
  `summary: {tests: 429, pass: 429, fail: 0, skipped: 0}`; the Qt-free interpreter resolves the 11
  environment-dependent skips that the local `npm test` run reports.
- `uv run python scripts/release_gate_check.py --run` → exit `0`: 4189 pytest passed, 94.45%
  coverage (floor 89), pyright 0 errors, ruff check/format pass, source package and smoke pass.
- `git diff --name-only -- desktop-electron/package-lock.json desktop-electron/package.json` → empty;
  `npm ci --registry=https://registry.npmjs.org` was used to populate the gitignored
  `node_modules/` and left the lockfile byte-identical.

### Verification corroboration

An independent verifier re-ran the scoped checks and corroborated every result above. The Slice B
scoped SDD contract is fully observed; the Slice B commit and the RDD/native review remain pending
as commit-lifecycle items, not verification gates.

### Release claim

The pre-existing no-release claim below still holds; Slice B adds no release, tag, DMG or
publication state.

## No release claim

v2.2.0 remains an unreleased source candidate per `openspec/changes/electron-publication-readiness/`.
This change makes no release, tag, DMG, PyPI or publication claim and requires none. Publication
stays owned by that change and by explicit authorization.
