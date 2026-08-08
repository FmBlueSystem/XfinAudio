# Archive Report: Modular Boundary Inventory

**Change**: `modular-boundary-inventory`
**Archived to**: `openspec/changes/archive/2026-06-18-modular-boundary-inventory/`
**Archived date**: 2026-08-08
**Artifact store mode**: openspec

## Why This Was Archived Late

The change reached `status: verify-complete` with `next_recommended: archive` on
2026-06-18 and then sat in `openspec/changes/` for seven weeks. Its own
`verify-report.md` § Dispatcher note already recorded the native dispatcher
reporting `nextRecommended: archive` with no blockers. Nothing was outstanding;
the archive step never ran. One of nineteen stale directories found by the
2026-08-08 audit.

## What Shipped

Two commits on 2026-06-18:

| Commit | Scope |
|---|---|
| `7d805d5` | `docs(architecture): inventory modular boundaries` |
| `203dbe8` | `refactor(recommendation): move candidate pool policy out of desktop` |

Surviving evidence on `main` at archive time:

| Deliverable | Location |
|---|---|
| Functional inventory document | `docs/architecture/functional-inventory.md` |
| Candidate-pool policy outside desktop | `src/xfinaudio/recommendation/candidate_pool.py:226` — `build_recommendation_pool` |
| Strategy-name domain resolver | `src/xfinaudio/recommendation/strategies.py:164` — `resolve_strategy_name` |

## Verification Verdict

**PASS** — recorded in `verify-report.md`.

- RED: focused run failed with missing `xfinaudio.recommendation.candidate_pool`
  and missing `resolve_strategy_name`.
- GREEN: same focused command, `35 passed in 0.47s`; the 10 previously failing
  Prep Copilot `tests/test_main_window.py` targets passed in the focused set.
- Full gate: `uv run pytest -q` 1023 passed; pyright 0 errors; coverage 90.19%;
  ruff check clean; ruff format 206 files already formatted; release gate PASS.
- Static dependency check: non-desktop modules do not import PySide6 or
  `xfinaudio.desktop`.

## Stale Citation — Recorded, Not Rewritten

Two historical artifacts in this directory cite a file that no longer exists:

| Artifact | Line | Claim |
|---|---|---|
| `apply-progress.md` | 11 | "Kept `src/xfinaudio/desktop/recommendation_presenter.py` as a compatibility wrapper." |
| `verify-report.md` | 31 | "Desktop compatibility maintained — `src/xfinaudio/desktop/recommendation_presenter.py` re-exports the moved functions." |

`src/xfinaudio/desktop/recommendation_presenter.py` is **absent** from `main`.
Both statements were **true when written**. The wrapper was deliberately removed
later, on 2026-06-20, by commit `f99ad33` (PR #280,
`refactor(desktop): remove recommendation presenter wrapper`) under the change
now archived at
`openspec/changes/archive/2026-06-20-remove-recommendation-presenter-wrapper/`.

That is the intended trajectory, not a defect: this change deliberately kept a
compatibility wrapper as a transitional step, and the successor removed it once
every consumer had moved to `xfinaudio.recommendation.candidate_pool`. The
boundary this change created survived; only the temporary shim went.

**The historical artifacts are left exactly as written.** Rewriting them to
match today's tree would falsify what was verified on 2026-06-18 and would
violate this project's own rule that archived history must not be rewritten
during reconciliation. The correction is recorded here instead.

Residual naming note, non-blocking: `tests/test_recommendation_presenter.py`
still exists and still carries the old name in its module docstring, but it now
imports `build_recommendation_pool` from
`xfinaudio.recommendation.candidate_pool`. The test is live and passing; only
its filename is a leftover of the retired wrapper.

## Specs Synced

**No.** This change carries `spec.md` and a `specs/` delta directory; no durable
capability spec is created or updated by this archive pass. Archiving here is a
lifecycle-record correction only, with no production change and no spec fold-in.

## Archive Contents

- [x] `proposal.md` — intent, problem, scope boundaries
- [x] `spec.md` and `specs/` — requirement delta
- [x] `design.md` — module ownership split
- [x] `tasks.md` — 5 tasks, all `[x]`
- [x] `apply-progress.md` — apply record (contains the stale citation above)
- [x] `verify-report.md` — TDD evidence, requirement table, static dependency check, dispatcher note
- [x] `state.yaml` — `status: verify-complete`, `next_recommended: archive`

## Task Completion

All 5 tasks `[x]`. Task 3 ("keep a compatibility wrapper") is historically
accurate and was superseded by `f99ad33`, as described above.

## Follow-Up Items

**(a) Rename `tests/test_recommendation_presenter.py` (OPEN, cosmetic).** The
file name and docstring reference a class and module that no longer exist. The
test itself is correct and covers `build_recommendation_pool`. Low value, zero
risk, not blocking.

## Archive Metadata

- **Created**: 2026-06-18
- **Updated**: 2026-06-18
- **Shipped**: 2026-06-18 (`7d805d5`, `203dbe8`)
- **Wrapper retired by successor**: 2026-06-20 (`f99ad33`, PR #280)
- **Archived**: 2026-08-08

**SDD Cycle Status**: COMPLETE — proposed, specified, designed, planned,
implemented, verified and archived. Spec fold-in not applicable (see Specs
Synced).
