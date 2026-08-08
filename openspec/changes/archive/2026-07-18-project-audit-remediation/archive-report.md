# Archive Report: Project Audit Remediation

**Change**: `project-audit-remediation`
**Archived to**: `openspec/changes/archive/2026-07-18-project-audit-remediation/`
**Archived date**: 2026-08-08
**Artifact store mode**: openspec

## The Blocker Was Superseded, Not Satisfied

**Read this section before citing this change as reviewed.**

This change was held open by one thing: an independent gentle-ai native review
transaction and receipt covering the **final native-corrected bytes**. Its
`state.yaml` recorded the position honestly and repeatedly, ending with
"Final RES-001 and READ-004 corrections pass focused and full gates; final
native re-review remains required," and an explicit refusal to fake it:
"Verification completion does not fabricate or grant a native review
transaction, ledger entry, receipt, or archive authority."

That position is respected here.

**No review transaction was opened. No ledger entry was written. NO RECEIPT WAS
OBTAINED.** Nothing in this archive should be read as evidence that the final
native re-review happened.

What changed is that the blocker became **unresolvable**, not met:

1. **The immutable candidate no longer exists.** A native review binds to a
   frozen revision. **103 commits** have landed on `main` since this change's
   last artifact commit `4da9fb9` (2026-07-18) — measured at archive time with
   `git rev-list --count 4da9fb9..HEAD`. The exact bytes the pending re-review
   was supposed to cover are no longer the working tree and cannot be re-frozen.
2. **Receipt-driven development is off for this clone.**
   `gentle-ai review mode status` reports
   `receipt-driven development: off (decided by clone_local)` — global `unset`,
   clone-local `off`. There is no review authority in this clone to issue a
   receipt from, and enabling it is the user's decision, not this pass's.
3. **The gated code is merged and shipped.** The remediation this gate covered
   is in `main` and released in v1.7.7. It is exercised by the ordinary release
   gates on every run, which is the repository policy that now governs it.

Holding a directory open forever against a review that can never execute is not
rigour; it is the exact stale-lifecycle defect this change itself specified
against (see below). It is archived with the gap stated, not papered over.

## State Correction

| Field | Before | After | Reason |
|---|---|---|---|
| `status` | `verify` | `completed` | Local gates pass; no work outstanding |
| `state` | *(absent)* | `completed` | Schema field was missing |
| `step` | *(absent)* | `archive` | Schema field was missing |
| `review_status` | *(absent)* | `waived` | **Not** `completed` — no receipt exists |
| `phases.verify` | `in-progress` | `complete` | On recorded local gate evidence only |
| `next_recommended` | `final-native-re-review` | `archive` | Non-standard token; no SDD phase implements it |

`review_status: waived` is deliberate. `completed` would assert a review that did
not happen. Five explanatory notes were appended to `state.yaml`; the fourteen
original notes are untouched.

### On the pre-existing owner waiver

`state.yaml` already records a *different*, narrower waiver: the Anthropic
cross-model review was unavailable and the owner explicitly waived that specific
missing check with the exact response "si, aprobado". That waiver covered the
cross-model check only. It is **not** a waiver of the final native re-review, and
is not reused as one here. The final native re-review is unwaived and
unperformed; it is superseded by circumstance, as described above.

## Closing This Change Fulfils Its Own Spec

This change specified the requirement **"Complete Active SDD Lifecycle Records"**
at `specs/project-maintenance-quality/spec.md:44-53`:

> Every active OpenSpec change MUST contain the artifacts required by project
> governance and MUST report a state consistent with repository evidence.
> Archived history MUST NOT be rewritten during reconciliation.
>
> Scenario: Active change is complete and coherent — GIVEN an OpenSpec change
> remains active, WHEN its lifecycle record is audited, THEN every required
> artifact MUST exist AND its phase status and next recommendation MUST agree
> with artifact evidence.

That is precisely the requirement the nineteen stale directories violated. Each
reported an active, unfinished state while its work had shipped — phase status
and `next_recommended` disagreeing with repository evidence.

This change was itself one of the nineteen. Its `next_recommended:
final-native-re-review` was a token no SDD phase implements, so its own
lifecycle record could not agree with any evidence by construction.

The 2026-08-08 cleanup satisfies this requirement's scenario across the whole
`openspec/changes/` tree, and closing this change is the last step of it. Its
sibling clause — "Archived history MUST NOT be rewritten during reconciliation"
— was honoured throughout: contradictions in
`2026-06-14-spectral-color-features` and
`2026-06-18-modular-boundary-inventory` were annotated in archive reports rather
than edited out of the historical artifacts.

## What Shipped

Remediation across test, dependency, lifecycle and module-structure findings,
delivered as autonomous PR slices per the change's own delivery strategy
(`chained_prs_recommended: true`, `chain_strategy: feature-branch-chain`), not as
one monolithic patch. Its `state.yaml` trail records the correction rounds:

- All five independent-review findings corrected, local gates green.
- R2 semantic dependency-policy and export-write characterization corrections.
- R3 final dead-constant cleanup, passing focused layout, Ruff and Pyright.
- Fresh-context same-family review converged 5 → 2 → 1 → 0; R4 CLEAN.
- Native 4R READ-001/2/3 and REL-001/2/3 corrections passing focused and full gates.
- Final RES-001 and READ-004 corrections passing focused and full gates.

Last artifact commit: `4da9fb9`, "docs(openspec): record final review
corrections" (2026-07-18).

## Verification Verdict

**PASS on local gates; UNREVIEWED by independent native review.**

The change's own notes record final verification passing, with one environmental
workaround stated plainly: Pyright required `OPENSSL_CONF=/dev/null` because the
managed host blocked Node from reading the system OpenSSL configuration.

At archive time the repository gates were re-run on `main` @ `9dce07d` with no
source change in this pass: `uv run pytest -q` 1510 passed; `uv run pyright src
tests` 0 errors, 0 warnings, 0 informations; `uv run ruff check .` all checks
passed; `uv run ruff format --check .` 279 files already formatted.

Local gates are the only verification claimed. See the top section for what is
not claimed.

## Specs Synced

**No.** This change carries `spec.md` and a `specs/` delta directory including
`project-maintenance-quality`. No durable capability spec is created or updated
by this archive pass, and no production source was touched.

Folding `project-maintenance-quality` into `openspec/specs/` would be a
reasonable follow-up, since the lifecycle requirement quoted above has now proven
its worth. It is listed below rather than done, because doing it silently during
a cleanup would itself be an unreviewed spec change.

## Archive Contents

- [x] `proposal.md` — audit findings and remediation intent
- [x] `spec.md` and `specs/project-maintenance-quality/spec.md` — requirement deltas
- [x] `design.md` — remediation approach
- [x] `tasks.md` — task plan
- [x] `apply-progress.md` — per-slice apply record including the PR4 corrective strict-TDD cycle
- [x] `verify-report.md` — verification evidence
- [x] `state.yaml` — 19-note decision trail, corrected as described above

## Follow-Up Items

**(a) Native re-review permanently unavailable for this candidate (CLOSED as
superseded).** Not resolvable; see the top section. If equivalent assurance is
wanted for the shipped code, it must be a **new** review over a **current**
candidate, which would require enabling receipt-driven development for this
clone — a user decision.

**(b) Fold `project-maintenance-quality` into `openspec/specs/` (OPEN).** The
lifecycle requirement at `specs/project-maintenance-quality/spec.md:44-53` is
durable, project-wide policy and is currently reachable only from this archived
change directory.

**(c) Guard against archive-by-copy (OPEN, tooling).** The root cause of all
nineteen stale directories was an archive step that copied instead of moved:
`4a00a61` created both `openspec/changes/archive/playlist-export-hardening/*`
and `openspec/changes/playlist-export-hardening/*` in one patch; `1f779fd`
correctly renamed lean-refactor PR2/PR3 but copied PR4/PR5; the nine UI-phase
PRs each added an archive copy with `status: completed` alongside an active copy
that never got the state flip. A check asserting that no name appears both in
`openspec/changes/` and `openspec/changes/archive/` would have caught every one.

## Archive Metadata

- **Created**: 2026-07-18
- **Updated**: 2026-07-18
- **Last artifact commit**: 2026-07-18 (`4da9fb9`)
- **Archived**: 2026-08-08
- **Commits between last artifact and archive**: 103

**SDD Cycle Status**: COMPLETE ON LOCAL EVIDENCE — proposed, specified,
designed, planned, implemented and locally verified. **Independent native review
NOT performed; superseded, not satisfied.** Spec fold-in not applicable to this
pass (see Specs Synced).
