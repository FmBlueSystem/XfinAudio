# Archive Report: Tighten Same Color & Energy

**Change**: `tighten-same-color-energy`
**Archived to**: `openspec/changes/archive/2026-08-08-tighten-same-color-energy/`
**Archived date**: 2026-08-08
**Artifact store mode**: openspec

## What Shipped

Three chained slices, `feature-branch-chain`:

| Slice | PR | Squashed commit | Scope |
|---|---|---|---|
| 1 | #332 | `1ac66c3` | Characterization safety net — test-only, zero production behaviour changed (version `1.6.1`) |
| 2 | #333 | `5fce223` | Strict color-and-exact-energy eligibility, MIXED bounded proximity gate, fail-closed, warnings, description (version `1.7.0`) |
| 3 | #334 | `a32d515` | Anchor binding through dedupe, cap, the application candidate seam and the desktop route (version `1.7.1`) |

- **Version across the chain**: `1.6.0` (base `cad0818`) → `1.7.1`, one bump per PR
- **Successor**: `tighten-spectral-color-filters` (PRs #336, #337) — extends this
  change's bounded gate from MIXED-only to every dominant-color label and renames
  its `MIXED_*` constants to `COLOR_*`

## Verification Verdict

**PASS** — `verify-report.md`, verdict recorded 2026-08-05 as
"PASS (both WARNINGs CLOSED 2026-08-05)", amended 2026-08-08 to
**"PASS — no residual items"** once the acceptance gate closed.

At verify time (2026-08-05): `uv run pytest -q` 1406 passed, pyright 0 errors,
coverage 91.16%, ruff check and format clean, release gate exit 0. All 6
requirements (1 ADDED + 5 MODIFIED, 12 scenarios) trace to implementation, and
all 12 scenarios have asserting tests after F1 was closed.

At archive time (`main` @ `4603d24`, 1.7.6): `uv run pytest -q` 1510 passed,
pyright 0 errors/0 warnings/0 informations, coverage 91.21%, ruff check clean,
ruff format 279 files already formatted, release gate PASS (PyInstaller
check-only; project-root `build/` and `dist/` absent).

## Acceptance Gate A.1 — CLOSED by measurement (2026-08-08)

This change shipped with one deliberately open, non-blocking acceptance gate: the
MIXED numeric constants were **calibration-provisional**, and the delta spec's
MUST attached to the rule shape rather than to the literals. That gate is now
closed.

- **Method**: read-only sweep over a scratch copy of the real library
  (`~/.xfinaudio/xfinaudio.sqlite3` → `/tmp/xfin-calib/scratch.sqlite3`); the live
  DB was **never** opened. 10,367 tracks with `metadata_status = 'complete'` and a
  non-null spectral profile (10,392 total), 40 anchors per dominant-color label,
  seed `20260808`, both `same_color` and `same_color_energy` pools.
- **Constant lineage**: the successor renamed `MIXED_RGB_L1_MAX` /
  `MIXED_CENTROID_REL_MAX` / `MIXED_ROLLOFF_REL_MAX` to `COLOR_RGB_L1_MAX` /
  `COLOR_CENTROID_REL_MAX` / `COLOR_ROLLOFF_REL_MAX`. **The values did not change
  with the rename**, so the calibration measured exactly the numbers this change
  introduced.
- **Outcome**: `0.08` / `0.15` / `0.15` **RETAINED UNCHANGED**. The provisional
  literals are confirmed by measurement. **No production source change results.**
- **Scope limit, stated honestly**: this is a pool-geometry measurement, **not a
  listening test**. Task A.1 as written asked for a listening pass around the
  MIXED thresholds; that pass did not happen. The maintainer signed off on the
  measured evidence instead.

Full evidence: `verify-report.md` § Calibration Closure (2026-08-08), and the
complete sweep tables in
`openspec/changes/archive/2026-08-08-tighten-spectral-color-filters/verify-report.md`
§ Calibration Evidence (recorded once, not duplicated).

## Specs Synced

**Yes.** This change's delta was folded into the durable capability spec:

| Capability | Action | Path |
|---|---|---|
| `same-color-energy-strategy` | Updated (pre-existing spec) | `openspec/specs/same-color-energy-strategy/spec.md` |

Order matters and was honoured: this change's delta was applied **first**, then
the successor `tighten-spectral-color-filters` was applied **on top** (it
overrides). The durable spec therefore describes current shipped behaviour under
the current `COLOR_*` constant names, never the retired `MIXED_*` names.

This closes part of the `spec_synced: false` debt recorded by
`2026-08-07-resolve-color-review-findings` and `2026-08-08-prep-copilot-color-anchor`,
both of which deferred the fold-in to whoever archived the colour-strategy
changes.

## Archive Contents

- [x] `proposal.md` — intent, the three defects, scope boundaries, success criteria
- [x] `spec.md` / `specs/same-color-energy-strategy/spec.md` — 6 requirements (1 ADDED + 5 MODIFIED, 12 scenarios)
- [x] `design.md` — eligibility predicate, anchor identity, fail-closed and warning ownership
- [x] `tasks.md` — Phases 1–7 plus acceptance gate A.1, all complete
- [x] `apply-progress.md` — per-slice RED→GREEN ledger, verify correction (2026-08-05)
- [x] `verify-report.md` — requirement-by-requirement evidence, findings, calibration closure
- [x] `exploration.md`, `CONTINUATION.md` — pre-proposal investigation and the design-gate history
- [x] `state.yaml` — full decision trail (29 notes)

## Task Completion

- Phases 1–7: all `[x]`, reconciled to shipped reality by the 2026-08-05 verify
  correction (finding F2).
- **A.1** (post-implementation acceptance gate): `[x]` as of 2026-08-08 — closed
  by measurement with the constants retained.

## Findings at Verify (all closed)

| ID | Severity | Status |
|---|---|---|
| F1 | WARNING | CLOSED 2026-08-05 — shortage-warning scenario had no asserting test; `test_same_color_energy_shortage_returns_only_eligible_and_warns` added. No production code changed. |
| F2 | WARNING | CLOSED 2026-08-05 — `tasks.md` checkbox and `state.yaml` drift under-claiming shipped work; reconciled. |
| S1 | SUGGESTION | Open, non-blocking — recurring test-line budget overage on strict-TDD work; the successor hit it a third time. A documented per-change test-line allowance would stop it being re-litigated. |
| S2 | SUGGESTION | Open, non-blocking — duplicate-version survivors observed end-to-end are **pre-existing** `dedupe_recommendation_duplicates` grouping behaviour keyed on title+artist, **not** a defect of this change. |

## Follow-Up Items

### (a) Calibration acceptance gate A.1 (CLOSED)

**Status**: Closed 2026-08-08 by the measurement described above. Constants
retained unchanged; no code change followed.

### (b) Test-line budget allowance for strict-TDD changes (OPEN, process)

`size:exception` was accepted three times across this change and its successor
(slice 2: 540 lines, slice 3: 436 lines, successor slice B: ~590 lines), each
time with production comfortably inside the 400-line budget and the entire
overage in test volume. This is a standing pattern, not an anomaly. Worth a
documented per-change test-line allowance so the exception stops being the rule.

## Archive Metadata

- **Proposed**: 2026-08-02
- **Specs / Design / Tasks**: 2026-08-02
- **Applied**: 2026-08-03 (slices 1–2), 2026-08-04 (slice 3)
- **Verified**: 2026-08-05 (corrected same day)
- **Calibration closed**: 2026-08-08
- **Archived**: 2026-08-08

**SDD Cycle Status**: COMPLETE — proposed, specified, designed, planned,
implemented, verified, calibration-closed, spec-synced and archived.
