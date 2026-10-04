# Feature: installable Electron 2.2.0

## Goal

Deliver a verifiable macOS installer for end users, not merely a green source
candidate. Preserve metadata-first DJ control and safe Serato export. A source
tag, draft release, or ad-hoc-signed app does not satisfy this goal.

## Baseline and constraints

- User confirmed the installable-app goal and authorized local feature-branch
  work-unit commits. Push, PR, release publication, and merge are not authorized.
- Baseline `main`/remote tag `v2.2.0`: `fc3f748`; exact-commit source and Electron
  checks succeeded. The draft release contains only source archives/checksums.
- Current Electron macOS recipe produces a local ad-hoc-signed development app,
  not a notarized DMG. This host has no valid Developer ID identity.
- Respect `AGENTS.md` and the local gentle-ai SDD/TDD skill. Keep every work unit
  reviewable within 400 changed lines, or obtain a chain decision before growth.
- A passing CI run is not a substitute for clean-account, audible, legal, and
  final-artifact acceptance. Do not publish the existing draft or move its tag.

## Work units

1. [ ] Lock the Electron IPC method contract across validation, dispatch, and
   preload. First prove a meaningful RED for fail-closed dispatch/exhaustiveness,
   then implement the smallest GREEN, run focused and applicable gates, and
   record a Conventional Commit on `feat/electron-ipc-contract`. Use a scoped
   OpenSpec change; avoid changing Python routes unless the invariant requires it.
   Acceptance: every allowed UI method reaches exactly one handler; unknown or
   unhandled methods fail explicitly, and a regression test catches drift.
   Evidence: verification complete — RED observed (`AssertionError: R1: action()
   must end in a throwing default arm`, exit 1), GREEN observed (focused guard
   exit 0), full Electron suite exit 0 (429 tests, 418 pass, 11 pre-existing
   skips, 0 fail), Qt-free wrapper exit 0 (429/429, 0 skipped), repo gate exit 0
   (4189 pytest passed, 94.45% coverage, pyright 0, ruff pass), drift
   triangulation passes; independent verifier corroborated. Still pending: the
   conventional commit on `feat/electron-ipc-contract` and the RDD/native review
   result.
2. [ ] Build a reproducible Electron macOS installer from an exact source commit,
   with bundled core, notices, provenance, checksum, and no project-root build
   artifacts. Acceptance: one documented invocation yields a DMG that opens on
   a clean macOS account; commit and tests stay within a reviewable slice.
   Evidence: pending.
3. [ ] Add Developer ID signing and notarization for that exact Electron build.
   Acceptance: `codesign`, `spctl`, stapling and clean-account Gatekeeper checks
   pass on the final DMG. Blocked until the owner supplies a valid identity and
   notary credentials; never store credentials in the repository.
   Evidence: pending.
4. [ ] Attach a hash-bound installer to a hosted CI packaging gate for the exact
   candidate commit. Acceptance: source seal, artifact SHA-256, tests and CI
   run identity reconcile; no release from red or unrelated-commit evidence.
   Evidence: pending.
5. [ ] Complete real-library, audible, Serato-export, clean-account, and binary
   redistribution/notices acceptance on the exact final bytes. Reconcile notes
   that currently say `v2.2.0` is not a tag. Acceptance: signed QA/legal record;
   only the human decides when to publish the draft release.
   Evidence: pending.

## Current task

Work unit 1 proceeds as two local commits on `feat/electron-ipc-contract`; no
push, PR, merge or publish is authorized. The earlier pause held because 473 SDD
artifact lines plus this plan exceed the 400-line budget as one commit.

- Slice A (documentation planning only): committed as
  `2422ffc7fa9cd02fcd2b0f7e138b1df092674723` (393 added lines). It contains
  this plan, `proposal/spec/design/tasks/state`, and minimal `apply-progress`/
  `verify-report` placeholders. Rollback: revert that docs-only commit. The
  staged index check confirmed only these paths and no whitespace errors.
- Slice B (behavior, strict TDD): the one-line fail-closed `default` arm in
  `main.ts`, the guard test (`desktop-electron/tests/ipc-contract.test.mjs`, now 63 readable lines
  with the R1 assertion at line 42; at the observed RED it was a 22-line file with R1 at line 14),
  and the expanded progress/report. Rollback: revert
  that single commit. Checks: the verify commands in `tasks.md`, in order. Status:
  RED/GREEN/triangulation and all four contract commands are observed green (Qt-free
  wrapper 429/429 with 0 skips; repo gate exit 0), independently corroborated. The
  Slice B commit and the RDD/native review remain pending; no commit has been made in
  this session.

Both slices stay under 400 added lines; unit 3 keeps its external credential blocker.
