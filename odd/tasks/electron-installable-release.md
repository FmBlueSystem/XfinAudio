# Feature: installable Electron 2.2.0 (personal, local)

## Goal

Deliver a verifiable, locally installable macOS **2.2.0** app and a QA-only DMG
for this owner's own Mac, not merely a green source candidate. Preserve
metadata-first DJ control and safe Serato export. Ad-hoc signing is acceptable
for this target, with an explicit Gatekeeper manual-open caveat. A source tag,
draft release, or ad-hoc-signed app still does not by itself satisfy this goal
until the real artifact exists and has been exercised.

## Audience decision and why the earlier target changed

The original target was a **public end-user release** artifact: an installer
suitable for distribution to third parties, which is why work unit 3 was scoped
to Developer ID signing and notarization and work unit 4 to a hosted CI
packaging gate for the exact candidate commit. That target required a valid
Developer ID identity and notary credentials, which this host does not have.

The owner has now narrowed the audience to **personal use on their own Mac**.
Under that decision: no Developer ID identity, no notarization, no hosted CI
artifact and no public release are required for the current target. The public
release target is deferred, not deleted — its history below is retained so the
reasoning stays auditable, and any future resumption reopens it explicitly
rather than silently assuming it.

## Baseline and constraints

- User confirmed the personal installable-app goal and authorized local
  feature-branch work-unit commits. Push, PR, release publication, and merge are
  not authorized.
- Baseline `main`/remote tag `v2.2.0`: `fc3f748`; exact-commit source and Electron
  checks succeeded. The draft release contains only source archives/checksums and
  is not part of this personal target; do not publish it or move its tag.
- Current Electron macOS recipe produces a local ad-hoc-signed development app,
  not a notarized DMG. This host has no valid Developer ID identity.
- **Source seal stability**: record the exact source commit before the gate and
  keep it unchanged for the whole build. All generated reports and build
  artifacts live outside the source tree, so they never enter `source_digest`
  scope.
- Ship no false output: mark a work unit complete only when its real evidence
  exists. Synthetic/QA-only builder results are not real-artifact evidence.
- Respect `AGENTS.md` and the local gentle-ai SDD/TDD skill. Keep every work unit
  reviewable within 400 changed lines, or obtain a chain decision before growth.
- No publish step and no distribution legal clearance claim is in scope here.

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
2. [x] Assemble and verify the exact, frozen inputs for a real local build.
   Required inputs: the owner's exact-source gate report plus a zero-skip
   Electron suite result for the same source seal, a native pinned environment
   (`uv pip sync --require-hashes` against the packaging lock), and the trusted
   local arm64 FFmpeg closure hash manifest with its explicit license inputs.
   Acceptance: every input is hash-recorded, tied to the recorded source commit,
   and re-checked against that seal; nothing is resolved from unknown downloads;
   generated reports stay outside the source tree.
   Status: verified for source commit `6c045f333baa76afcfe599ce900b1414a90c1ade`
   and source digest `a38ff0fbfc260eb3f69c8dab91d6559c7e42005c75ade26deebb984d5e1e8f68`.
   Raw gates passed 10/10; the separately preserved sealed report includes the
   observed Qt-free Electron result (429 passed, zero skipped). Node 24.4.1,
   Electron 44.5.1 arm64 and the 37-package hash-locked native Python environment
   were checked; the 92-member Homebrew FFmpeg arm64 closure and every binary hash
   matched its external manifest. The external license directory holds 95 copied
   texts and discloses one missing leptonica text; personal use only, not clearance.
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
   Synthetic fake runner only: no real app, DMG or `hdiutil` call. The owner has
   now authorized preparing a personal local install; no real `.app`/DMG build
   starts until a fresh exact-source gate seal and native inputs are verified per
   `packaging/macos/README.md`. Developer ID is not needed for this
   personal target and remains unavailable; no electron-builder, no legacy Qt DMG
   script, and `build.py` stays untouched.
   Evidence commit: `50c7271a096e87a78d008c83493ad15e22b6599f`
   (97 documentation diff lines). Native INSPECT on the clean committed tree
   returned `empty_candidate_base_ref_required`; no START route was offered, no
   lineage or review receipt exists. The exact code commit has not been separately
   ASSESSed; do not infer review approval from the branch state.
   Build inputs and raw/sealed reports are preserved under
   `/Users/freddymolina/Desktop/XfinAudio-personal-qa-6c045f3/`; source stayed
   clean and unchanged throughout the gate and build. A real app and QA image
   were subsequently generated from this frozen source; see work unit 3 for
   their independent integrity evidence. Clean-profile launch and audio QA
   remain separate work units.
3. [x] Build the real `.app` and the QA-only DMG outside the source tree from
   frozen source commit `6c045f333baa76afcfe599ce900b1414a90c1ade`.
   Evidence: one `packaging/macos/build.py` run created the 684 MB arm64
   `XfinAudio Next.app` with a post-signing native manifest and valid ad-hoc
   `codesign --verify --deep --strict`; one `packaging/macos/dmg.py` run created
   `/Users/freddymolina/Desktop/XfinAudio-personal-qa-6c045f3/app-build/XfinAudio Next QA.dmg`
   (315853849 bytes). Its SHA-256 is
   `5f973b9cb507f77827ba5d908e9fbcec6c1f773655303ef1045406b157586ae8`;
   the sibling checksum and provenance agree. Independent read-only mounting
   confirmed only the app and `/Applications` shortcut, arm64 2.2.0 identity,
   signatures and embedded source seal; `hdiutil verify` passed and the image
   detached cleanly. No project-root `build/` or `dist/`; worktree was clean
   during build. `PERSONAL-QA-README.md` beside the image records per-app
   Gatekeeper manual-open guidance; Developer ID/notarization are unnecessary
   for this personal target. No installation or launch is claimed here.
4. [ ] Open the real app for the owner's personal use in the existing macOS
   account, then verify its first-launch behavior and actual
   `userData`/session/log/crash paths. The owner explicitly declined the extra
   test-account requirement; no separate account is needed for personal use.
   Existing `~/Library/Application Support/XfinAudio Next` has live data, so a
   launch may change it. Recommend a backup before opening; never claim that
   live data remained untouched or that clean-account QA passed. Packaged mode
   ignores development `XFIN_DATA_DIR`. The selected UI CLI `orca` is unavailable
   (exit 127), so the agent cannot drive Finder or inspect the app window here.
   Evidence: DMG mounted read-only; app not launched or installed, profile effects
   unknown. The owner can open it locally after considering the data risk.
5. [ ] Run functional personal acceptance on the final artifact bytes: listening
   playback (preview, pause, seek/resume, switch), library/metadata scanning on
   fixtures, and a safe Serato crate export; optionally repeat on the owner's real
   library only with explicit approval. Acceptance: recorded functional evidence
   bound to the artifact hashes, with the owner confirming audible and functional
   behavior. This is a personal-use decision only: it claims no redistribution
   rights, no legal clearance and no publication, and only the human decides
   whether any wider target is ever resumed.
   Evidence: pending.

## Current task

Work units 1–3 have verified outcomes. The real app and QA DMG are tied to
source commit `6c045f3`, not later documentation commits. The owner now wants
first launch in their existing macOS account; a separate test account is not a
prerequisite. Warn that existing XfinAudio userData can change and offer a backup
before opening. UI automation is unavailable, so no app launch or installation
has been observed. Work unit 5 remains functional personal listening, library
and Serato-export acceptance. No push,
PR, merge, publication or distribution legal clearance is claimed.
