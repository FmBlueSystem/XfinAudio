# Verify report

## Status

**Applied and verified (Slice B).** The one-line fail-closed `default` arm and the guard test are in
place under strict TDD. All four commands in the contract below were executed and are green, and an
independent verifier corroborated them. The remaining work is commit-lifecycle only: the Slice B
commit and the RDD/native review are pending on `feat/electron-ipc-contract`. This report claims no
release and no publication.

## Verification contract (to run during apply, in this order)

| # | Exact command | Observed |
|---|---|---|
| 1 | `cd desktop-electron && npm run build && node --test tests/ipc-contract.test.mjs` | RED: build exit `0`, test exit `1`, `# pass 0 / # fail 1`, `AssertionError: R1: action() must end in a throwing default arm` (historical RED location `ipc-contract.test.mjs:14` in the 22-line draft; the assertion is now at line 42 of the 63-line file). GREEN: build exit `0`, test exit `0`, `# tests 1 / # pass 1 / # fail 0`. |
| 2 | `cd desktop-electron && npm test` | Exit `0`; `# tests 429 / # pass 418 / # fail 0 / # cancelled 0 / # skipped 11 / # todo 0`. The 11 skips are the pre-existing environment-dependent integration tests. |
| 3 | `XFIN_PYTHON=/path/to/qt-free/python python scripts/electron_ci_check.py` | Exit `0`. `.release-evidence/electron-test-report.json`: `status: passed`, `returnCode: 0`, `summary: {tests: 429, pass: 429, fail: 0, skipped: 0}`. The Qt-free interpreter resolves the 11 environment-dependent skips from the local `npm test` run. |
| 4 | `uv run python scripts/release_gate_check.py --run` | Exit `0`: 4189 pytest passed, 94.45% coverage (floor 89), pyright 0 errors, ruff check/format pass, source package and smoke pass. |

Coverage floor is owned by `pyproject.toml` (`[tool.coverage.report] fail_under`); never pass
`--cov-fail-under` on a command line.

## Requirement evidence ledger (to be filled with observed output)

| Requirement | Evidence | Observed |
|---|---|---|
| R1 unhandled allowlisted action fails closed | assertion 1 of `ipc-contract.test.mjs` (RED before, GREEN after) | RED exit `1` with `AssertionError: R1: action() must end in a throwing default arm`; GREEN exit `0`. |
| R2 three-way parity A = S = P | assertions 2-3 of `ipc-contract.test.mjs` | GREEN; baseline enumeration `A=60 S=60 P=60`; removed switch case, removed allowlist key and preload mismatch each flip the guard to failure (see apply-progress). |
| R3 preload key equals dispatched action | assertion 4 of `ipc-contract.test.mjs` | GREEN; in-memory `listLibrary -> getMetadataReport` mismatch flips `key equals method` to `false`. |
| R4 unknown action rejected before any host | existing suites (`security.ts:49` gate); unchanged by this change | Covered by command 2 green; `main.ts` unchanged except the `default` arm. |
| R5 allowlisted actions recognized by the validator | runtime probe, assertion 5 of `ipc-contract.test.mjs` | GREEN: every dispatched action is recognized by `validateRequest` (no `Unsupported action`). |
| R6 no behavior or surface change | commands 2 and 3 | Command 2 green with 0 failures; command 3 exit `0`, 429/429 with 0 skips. |

## Disclosures

- The R1 RED is a source-level assertion, not a behavioral one: no allowlisted-but-undispatched
  action exists today, so the runtime path cannot be triggered without first changing the
  allowlist. The larger alternative that would make it a pure runtime test (a single exported
  dispatch table) is recorded in `design.md` as out of scope for this work unit.
- Parity was confirmed at 60/60/60 as proposal-phase evidence by read-only source enumeration only;
  that enumeration is not a substitute for command 1's executed evidence.
- Baseline before apply: the full Electron suite was not run before the change. The 11 skipped
  tests in command 2 are environment-dependent integration tests that skip without their fixtures;
  none is a new failure and none is caused by this change.
- All four commands were executed and observed green; an independent verifier re-ran the scoped
  checks and corroborated them. The Slice B commit and the RDD/native review remain pending and are
  not verification gates.

## Release claim

None. This report asserts no release readiness and no publication on its own. The publication
state remains that of `openspec/changes/electron-publication-readiness/`, which this change links
to and does not modify. Any accepted source change during apply invalidates prior evidence and
requires a fresh run of commands 1-4.
