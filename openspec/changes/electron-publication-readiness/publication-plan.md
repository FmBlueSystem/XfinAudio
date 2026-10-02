# Source publication and review chain

## Identity and isolation

Read-only remote check, 2026-10-01 22:51 UTC: PR360 is a draft at `dd15f0dffb9d524169d9559e538e23afb23861a4` on `fix/audit-2026-09-30`; main remains `a812f26cb0d9f3bf5a6e7265e00f032f9b426b1b`. The independent `fix/watcher-event-lifecycle` branch is `a906196df378fa0b486ffaad3f40eae040a0fe7a`, six commits ahead of dd15f0d. Its five changed files have zero overlap with V12 or this follow-up. This observation is not a permanent ref lock: re-read refs before publication and reconcile unexpected movement.

V12 remains immutable: archive SHA256 `7144db1cf8cbd35f4a7dcf5deb81d01417d888d6d50e06012d38d0003d4eb12b`, source seal `27c50a0de99603ae18453f477076e71d109fe746daff4dd6a3bdb9c2805bbc7a`, computed Git tree `89eab4bd6521fbb84abe9ce288e5db353e6cd874`. Its delta is 375 files (360 added, 15 modified, 0 deleted), +27,306/-330 text lines plus eight synthetic FLACs. The local Mac V12 app is not a 2.2.0 build. The final follow-up seal/diff and local gate results must be recorded separately after all edits stop.

Proposed new branch: `feat/qt-free-electron-2.2.0`, starting at dd15f0d. Do not append to PR360 or the watcher branch. The initial source-review draft depends on PR360 and targets `fix/audit-2026-09-30`; later child PRs target the previous chain stage. Do not target main and duplicate the audit stack. Retarget only after dependency integration, a fresh diff and exact-source verification. No force-push, merge, tag, release, binary upload or remote mutation is performed by this preparation.

## Explicit budget/chain plan

AGENTS permits exceeding 400 changed lines only with an explicit chained-PR plan. This is that plan, not a declaration that a 27k-line integration is a small review. Preserve meaningful feature dependencies and existing RED/GREEN evidence. Never invent original commit history, retroactively claim each reconstructed commit was tested, or create empty/dummy commits. Tests and implementation belong in the same reviewable behavior boundary; generated locks and historical evidence are labeled separately.

Ordered review stages (each with its related tests and seven SDD artifacts):

1. **Local protocol and Qt-free boundaries:** application query/live/metadata extractions; JSONL server, cancellation, core/backend contracts; hash-locked headless environment
2. **Sandboxed host and audio identities:** main/preload IPC, sender validation, canonical profiles, audio range protocol and lifecycle
3. **Library, Prep and saved editing:** renderer shell, eleven strategies/three variants, save/reopen/editor; original local engine authority
4. **Serato and metadata worklists:** immutable selected-destination preview/confirmation, anchored writer, backups, exact filtered worklists
5. **Live, preferences and watcher:** manual assistance/history, persistence, interrupted/dirty-close flows, Qt-free observation lifecycle
6. **Loudness:** exact scopes, explicit confirmation, original writer/byte backups and truthful partial outcomes
7. **Optional AI:** fixed recipient, selected credential-file identity, original timeout policies, eight surfaces, fake-provider-only acceptance
8. **Completion and data safety:** real spectral/danceability/edge completion, review controls, offline filters/saved actions and explicit safe legacy import
9. **Verification/source handoff:** whole-manifest coverage runner, completeness/identity checks, archive hygiene and reproducible seals
10. **Self-contained runtimes:** Linux recipe/cache/FFmpeg provenance and native Mac adaptation/packaged identity; platform validation remains distinct
11. **2.2.0 source readiness:** this follow-up's metadata/notes, CI gate enforcement, and dependency inventory; three coherent review units described below

Before constructing a PR, list exact changed files/hunks and text-line totals against its declared parent. Subdivide stages into real dependency-aligned review units targeting <=400 changed implementation/test lines. Where an indivisible existing file or generated lock exceeds that target, declare its exact count, reason and reviewer focus in the relevant stage; do not silently exempt it or refactor the verified runtime solely to manufacture a smaller diff. This is the explicit large-change/chain path, not a blanket claim of a maintainer-approved size exception. Any stricter repository check or requested approval remains a publication blocker, not a reason to bypass it.

Known larger baseline units require transparent review scheduling: renderer/app.ts916lines, headless/backend.py498, Serato export tests518 and anchored-writer tests436, Linux package tests411, profile tests409 and Prep parity tests408. Generated locks are separate reproducibility reviews (Linux970, headless882, npm569 lines in V12), not nine hundred hand-authored behavior changes. The integration draft may show the complete final source for context, but must link this ordered review plan and remain unready until its required reviews/CI are satisfied. No thousands of artificial commits or automatic approval claims.

## This follow-up's commit plan

- `chore: prepare 2.2.0 migration source candidate`: synchronized Python/Node metadata and own-package lock versions, beta/source notes, current-entry documentation, metadata regression and SDD/chain records. No dependency resolution changes or binary rebuild
- `ci: verify sharded Python and complete Electron suites`: existing whole-file shard mode in both aggregate paths; separate Electron job with pinned Node, locked Qt-free interpreter, actual npm test execution, no-skip/failure/cancellation checks and raw evidence; focused regressions
- `docs: inventory Qt-free migration dependencies`: clearly labeled legacy inventory plus all pinned headless/npm/toolchain provenance, documentation regression and explicit remaining binary-review obligations

The frozen CI unit is 358 changed text lines (workflow +65/-2, helper 98, new CI tests 174, existing action-pin inventory +18/-1); the dependency-inventory unit is 196 (inventory +131/-6, tests 59). The metadata/docs/SDD unit is separately counted in the final external manifest and must remain within 400. Compute final totals before committing. Split genuinely independent tests/helper/wiring or documentation boundaries if needed; retain explicit review dependencies. Do not invent an original RED/GREEN commit sequence: the preparation records actual observed RED/GREEN runs on the source tree. Gate the final combined tree and verify its published tree if publication is later authorized.

## Verification and release boundary

Local source gate: `uv run python scripts/release_gate_check.py --run --coverage-batch-size 120 --coverage-evidence-dir EXTERNAL/coverage --report-json EXTERNAL/release-report.json`, under the pinned legacy verifier, plus the new Electron CI runner with explicit Qt-free XFIN_PYTHON. Preserve the unchanged pyproject coverage floor and complete manifest; no selected-test substitute. Store raw logs and before/after source seals outside the checkout. Hosted CI is pending until an actual remote commit runs successfully.

Current same-version CI would reject exact V12 against PR360; the coherent 2.2.0 metadata resolves that without touching V12. The new workflow preserves read-only permissions. If a supported publication route lacks workflow-write permission, report that exact blocker; do not expand credentials or use an alternate identity. Binary notices/corresponding-source closure, notarization/distribution, human/audible acceptance, real-provider behavior and extended-library testing remain separate pending matters. No legal clearance is implied.
