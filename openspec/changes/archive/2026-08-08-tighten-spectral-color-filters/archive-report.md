# Archive Report: Tighten Spectral Color Filters

**Change**: `tighten-spectral-color-filters`
**Archived to**: `openspec/changes/archive/2026-08-08-tighten-spectral-color-filters/`
**Archived date**: 2026-08-08
**Artifact store mode**: openspec

## What Shipped

Two chained slices, `feature-branch-chain`, split along strategy lines:

| Slice | PR | Squashed commit | Scope |
|---|---|---|---|
| A | #336 | `c9f38c8` | `same_color_energy`'s bounded proximity gate spans every dominant-color label (the `!= "MIXED"` early return deleted); `MIXED_*` → `COLOR_*` constant rename, values unchanged (version `1.7.1 → 1.7.2`) |
| B | #337 | `60ffaf8` | `same_color` gets its own bounded colour gate and **fails closed** on an empty strict pool; the label-only `_apply_color_filter` / `_resolve_anchor_color` / `_track_color` helpers and `_COLOR_FILTER_STRATEGIES` removed (version `1.7.2 → 1.7.3`) |

- **Predecessor**: `tighten-same-color-energy` (PRs #332–#334) — this change
  extends its MIXED-only gate to every colour and renames its constants
- **Maintainer decision carried into spec**: `same_color` fails closed rather
  than widening to the unfiltered library. The proposal flagged it for sign-off;
  the delta spec committed to it; slice B shipped it.

## Verification Verdict

**PASS** — `verify-report.md`, written 2026-08-08 against `main` at `4603d24`
(version 1.7.6).

| # | Command | Result |
|---|---------|--------|
| 1 | `uv run pytest -q` | `1510 passed, 180 warnings in 52.21s` |
| 2 | `uv run pyright src tests` | `0 errors, 0 warnings, 0 informations` |
| 3 | `uv run pytest --cov --cov-fail-under=70 -q` | `1510 passed`, total coverage `91.21%` |
| 4 | `uv run ruff check .` | `All checks passed!` |
| 5 | `uv run ruff format --check .` | `279 files already formatted` |
| 6 | `uv run python scripts/release_gate_check.py --run` | PASS — PyInstaller check-only; project-root `build/` and `dist/` absent |

All 7 requirements across the two delta specs
(`same-color-strategy` 3 ADDED + 1 MODIFIED; `same-color-energy-strategy`
2 MODIFIED + 1 ADDED — 18 scenarios) trace to implementation, and **18/18
scenarios have asserting tests**. Findings: **CRITICAL 0 · WARNING 0 ·
SUGGESTION 2**.

## Acceptance Gate — tasks 4.1 / 4.2 CLOSED by measurement (2026-08-08)

Slice A and slice B both shipped with Phase 4 (the offscreen scratch-DB
calibration harness) marked `🔲 DEFERRED` — a calibration acceptance gate, never
a code blocker. Both are now closed.

- **Method**: read-only sweep over a scratch copy of the real library
  (`~/.xfinaudio/xfinaudio.sqlite3` → `/tmp/xfin-calib/scratch.sqlite3`); the live
  DB was **never** opened. 10,367 tracks with `metadata_status = 'complete'` and a
  non-null spectral profile (10,392 total), 40 anchors per dominant-color label,
  seed `20260808`, **both** `same_color` and `same_color_energy` pools, across
  MIXED / RED / GREEN / BLUE. Run as a direct sweep over the pure predicate rather
  than an offscreen `MainWindow`: the gate is a pure function of cached profile
  values, so this measures exactly what a UI run would, with no Qt surface and no
  write path.
- **Headline numbers**: median `same_color` pool MIXED 725 / GREEN 522 / BLUE 258
  / RED 152; 1 of 160 sampled anchors produced an empty `same_color` pool, and
  that anchor is a spectral outlier (centroid 5626 Hz against a library-typical
  ~1300 Hz).
- **Binding axis identified**: `COLOR_RGB_L1_MAX` binds for **every** colour
  (18–34% of the label-equal base pool passes L1 alone, against 44–81% for
  centroid and rolloff). The two relative-delta bounds at `0.15` are
  near-saturated — raising either to `0.50` moves the pool under 6% in every
  colour — so they are a cheap backstop against spectral outliers, not the
  primary filter. Lowering them to `0.10` *would* bite (~15–20%), so `0.15` sits
  just past the saturation knee rather than being an arbitrary ceiling.
- **Outcome**: `COLOR_RGB_L1_MAX = 0.08`, `COLOR_CENTROID_REL_MAX = 0.15`,
  `COLOR_ROLLOFF_REL_MAX = 0.15` **RETAINED UNCHANGED**. The provisional literals
  are confirmed by measurement; the delta specs' MUST attaches to the rule shape,
  and the rule shape is unchanged. **Zero production source change results.**
- **Scope limit, stated honestly**: this is a pool-geometry measurement, **not a
  listening test**. The maintainer signed off on the measured evidence without a
  separate listening pass.
- **Scripts**: the sweep scripts live in `/tmp/xfin-calib/` and are deliberately
  **not** added to the repository — the declared post-calibration change surface
  is constants plus artifacts only, and the constants did not change.

Full tables (per-axis pass rates, one-axis-dropped pools, three bound sweeps,
admitted-spread percentiles, the three outlier anchors) are recorded once, in
`verify-report.md` § Calibration Evidence.

## Specs Synced

**Yes — this is where the deferred fold-in finally happened.** Both
`2026-08-07-resolve-color-review-findings` and
`2026-08-08-prep-copilot-color-anchor` archived with `spec_synced: false`, each
naming this change as the place the durable colour-strategy behaviour belonged.
That debt is now paid.

| Capability | Action | Path |
|---|---|---|
| `same-color-energy-strategy` | Rewritten (pre-existing spec) | `openspec/specs/same-color-energy-strategy/spec.md` |
| `same-color-strategy` | Created (from delta) | `openspec/specs/same-color-strategy/spec.md` |

**Order applied**: predecessor `tighten-same-color-energy` **first**, then this
change **on top** (it is the successor and overrides). The end state describes
current shipped behaviour under the current `COLOR_*` constant names — the
retired `MIXED_*` names appear nowhere in the durable specs.

Both durable specs were checked against the real source in
`src/xfinaudio/recommendation/playlist_service.py` at `4603d24` before being
written, and describe the shipped gate as it stands today: one predicate
`_color_eligible(anchor, candidate, match_energy=...)` parameterized by the
frozen `_ColorGate` dataclass, with `COLOR_FILTER_STRATEGIES` as the single
dispatch answer, and `same_color` failing closed on an empty strict pool.

## Archive Contents

- [x] `proposal.md` — intent, the empirical case against label-only RGB filtering, the flagged fail-closed decision
- [x] `specs/same-color-strategy/spec.md` — 3 ADDED + 1 MODIFIED requirements (7 scenarios)
- [x] `specs/same-color-energy-strategy/spec.md` — 2 MODIFIED + 1 ADDED requirements (11 scenarios)
- [x] `design.md` — five architecture decisions, data flow, pool impact forecast, declared characterization exception
- [x] `tasks.md` — Phases 0–5, all complete (4.1 / 4.2 closed 2026-08-08), plus the declared prompt-scope deviation
- [x] `apply-progress.md` — per-slice RED→GREEN ledger, blast-radius fixes, dead-code call-graph verification
- [x] `verify-report.md` — requirement-by-requirement evidence, calibration evidence, findings, verdict
- [x] `state.yaml` — full decision trail (18 notes)

No `spec.md` at the archive root: this change carries **two** capability deltas,
and the repo convention for multi-capability archives
(`2026-07-20-strategy-ux-clarity-and-dedupe`, `qa-manual-mik-evidence`,
`xfinaudio-audio-preview`) is `specs/<capability>/spec.md` only. The root
`spec.md` copy is the single-capability convention.

## Task Completion

- Phase 0 (safety net) 0.1–0.3 — complete; the inventory proved existing
  predecessor coverage already sufficed, so 0.2 added nothing.
- Phase 1 (slice A) 1.1–1.10 — complete.
- Phase 2 (slice B) 2.1–2.11 — complete.
- Phase 3 (version + lock) 3.1–3.2 — complete, per-slice bumps.
- Phase 4 (calibration harness) **4.1, 4.2** — `[x]` as of 2026-08-08.
- Phase 5 (verification) 5.1 — complete.

## Declared Deviations (both flagged rather than followed blindly)

1. **Characterization exception wider than the prompt stated.** The slice-B
   prompt named two `_apply_color_filter_*` characterization tests as the
   declared exception. Six more predecessor end-to-end `same_color`
   characterization tests (`tests/test_playlist_service.py:295-381`) pinned the
   same deliberately-replaced contract and could not stay green. All eight were
   **re-authored, not deleted**, each with a docstring recording why. The
   prompt's "only two tests" premise was inaccurate and was reported as such.
2. **Blast radius wider than the task line-pointers implied.**
   `SpectralProfile` defaults `centroid_hz = rolloff_hz = 0.0`, so once RGB
   anchors started flowing through the gate, every test helper that built RGB
   tracks with zero features began failing closed. Fixed at the root by giving
   `spectral_track`, `test_application_recommendation_candidates._spectral_record`
   and `test_candidate_pool._spectral_record` finite positive values
   (`1000.0` / `2000.0`).

## Findings at Verify

| ID | Severity | Note |
|---|---|---|
| — | CRITICAL | None. |
| — | WARNING | None. |
| S1 | SUGGESTION | This change's helper names no longer exist; the behaviour does. `_same_color_eligible` / `_apply_same_color_filter` / `_same_color_warnings` (and the predecessor's `_same_color_energy_*` trio) were unified by `resolve-color-review-findings` (PR #339, `201e001`) into `_color_eligible` / `_apply_color_filter` / `_color_filter_warnings` parameterized by `_ColorGate`. `design.md` and `apply-progress.md` keep the shipped-then names as historical record; `verify-report.md` is the bridge. **Trap for future readers**: `_apply_color_filter` exists again under its old name with a *different* contract (gate-parameterized, fails closed) — it is not the label-only helper this change removed. |
| S2 | SUGGESTION | Test-volume budget overage, third occurrence across this change and its predecessor. Slice B is ~590 authored changed lines (source 159, tests 429) against a 400-line budget; the entire overage is per-colour test coverage for one atomic work unit. Accepted as `size:exception`. A documented per-change test-line allowance for strict-TDD work would stop it being re-litigated. |

## Follow-Up Items

### (a) Calibration acceptance gate 4.1 / 4.2 (CLOSED)

**Status**: Closed 2026-08-08. Constants retained unchanged; no code change
followed. See the Acceptance Gate section above.

### (b) Method note worth reusing for the next calibration (INFORMATIONAL)

Measuring "percentage of the base pool passing each axis **alone**" together with
"pool size if that axis is **dropped**" identifies the binding constraint
reliably. Single-anchor spot checks do not: an earlier, narrower measurement had
misidentified GREEN as centroid/rolloff-bound when it is in fact L1-bound like
every other colour. Anyone recalibrating these three constants should run both
views before concluding anything.

### (c) Test-line budget allowance for strict-TDD changes (OPEN, process)

Shared with the predecessor's follow-up (b). Three accepted `size:exception`
decisions across the two changes, every time with production inside budget and
the overage entirely in tests.

## Archive Metadata

- **Proposed / Specs / Design / Tasks**: 2026-08-02
- **Applied**: 2026-08-02 (slice A and slice B)
- **Verified**: 2026-08-08
- **Calibration closed**: 2026-08-08
- **Archived**: 2026-08-08

**SDD Cycle Status**: COMPLETE — proposed, specified, designed, planned,
implemented, verified, calibration-closed, spec-synced and archived.
