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

1. [x] Lock the Electron IPC method contract across validation, dispatch, and
   preload. Test-first RED proved the missing fail-closed arm; GREEN added the
   smallest fix and a parity guard. No Python route changed.
   Evidence: `2422ffc7fa9cd02fcd2b0f7e138b1df092674723` (planning, 393 lines)
   and `9bdb05c8280c97a26e29adf821a173d3de46c357` (behavior, 328 diff lines).
   RED failed R1, GREEN passed; full Electron suite exited 0 with 11 environment
   skips, Qt-free wrapper passed 429/429 with zero skips, canonical Python gate
   passed 4189 tests at 94.45% coverage (floor 89), pyright/ruff/smoke passed;
   independent verification corroborated. Native ASSESS for the exact committed
   slice: medium risk, `reviewDue: false` (`under_budget`), `consumed: false`.
   INSPECT found no pending workspace diff, so no START was offered; no review
   receipt, approval, or delivery authority is claimed.
2. [ ] Build a reproducible Electron macOS installer from an exact source commit,
   with bundled core, notices, provenance, checksum, and no project-root build
   artifacts. Acceptance: one documented invocation yields a DMG that opens on
   a clean macOS account; commit and tests stay within a reviewable slice.
   Status: QA-only prototype slices complete; final build and clean-account QA blocked.
   Scoped change: `openspec/changes/electron-dmg-local-validation`.
   Slice 1 (docs only): specifies a separate credential-free `packaging/macos/dmg.py`
   that consumes an already-built `XfinAudio Next.app` and its sibling
   `.native-manifest.json`, validates source digest/manifest/provenance and a QA-only
   name, stages the app with an `/Applications` symlink, runs `hdiutil create`/`verify`,
   writes a sibling SHA-256 and QA provenance, rejects existing output, source-tree
   output and symlink escapes, and never modifies the sealed app.
   Slice 2 (behavior, strict TDD, <400 lines): planning commit `ed855c9`
   (209 lines), then behavior commit `3fabf88` (392 added lines:
   `packaging/macos/dmg.py` 152, `tests/test_macos_dmg.py` 224, README 16). RED failed
   15 tests on the missing module; a second RED covered two safety defects (streaming
   digest and partial-evidence cleanup), then GREEN. Final focused
   `uv run pytest tests/test_macos_dmg.py tests/test_macos_recipe.py -q`: 28 passed;
   ruff/format/pyright clean on the changed files; canonical
   `uv run python scripts/release_gate_check.py --run` exit 0 (4205 pytest passed,
   94.45% coverage vs 89 floor, pyright 0, ruff/smoke/source hygiene green).
   Synthetic fake runner only: no real app, DMG or `hdiutil` call. No real `.app` or
   DMG build until the owner supplies the exact V11 seal and authorization per
   `packaging/macos/README.md`; Developer ID is unavailable; no electron-builder, no
   legacy Qt DMG script, and `build.py` stays untouched.
   Evidence commit: `50c7271a096e87a78d008c83493ad15e22b6599f`
   (97 documentation diff lines). Native INSPECT on the clean committed tree
   returned `empty_candidate_base_ref_required`; no START route was offered, no
   lineage or review receipt exists. The exact code commit has not been separately
   ASSESSed; do not infer review approval from the branch state.
   No real artifact, full delivery, clean-account open or clean-account QA result
   yet, so this work unit stays `[ ]` pending owner V11 seal/build authorization.
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

Work unit 2 has a verified synthetic QA-image builder in three local commits:
`ed855c9` (planning), `3fabf88` (code, tests and README), `50c7271`
(verification evidence). Each slice stays under 400 changed lines. Next, the owner
must integrate and authorize the exact V11 source seal and its gate report, plus
trusted FFmpeg closure and dependency-license inputs, before any real `.app`/DMG
build. A real image then needs mounted-image integrity checks and clean-account
startup QA; work unit 2 remains open. No push, PR, merge or publication is
authorized. Unit 3 separately awaits Developer ID and notary credentials.
