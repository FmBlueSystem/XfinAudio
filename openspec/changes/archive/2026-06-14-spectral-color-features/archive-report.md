# Archive Report: Spectral Color Features

**Change**: `spectral-color-features`
**Archived to**: `openspec/changes/archive/2026-06-14-spectral-color-features/`
**Archived date**: 2026-08-08
**Artifact store mode**: openspec

## Why This Was Archived Late

Its `state.yaml` was **malformed** — five lines, no `schema:`, no `status:`, no
`created:`/`updated:`, no `phases:` map, no `delivery:` block, no
`next_recommended:`, and a non-standard `phase:` key where the schema expects a
`phases:` map. No dispatcher could route a record that shape, so the change was
never eligible for an archive transition. One of nineteen stale directories found
by the 2026-08-08 audit.

The record is rewritten to `gentle-ai.sdd-state.v1` in this pass. The three
fields the old file did carry (`state: completed`, `step: verify`,
`review_status: completed`) are preserved in meaning; `step` advances to
`archive` to match this transition.

## Not Superseded — Read This Before Assuming Otherwise

This change owns the spectral **ANALYZER**: the code that listens to a file and
produces a `SpectralProfile`. It is **not** superseded by the colour-strategy
work archived on 2026-08-08 (`2026-08-08-tighten-same-color-energy`,
`2026-08-08-tighten-spectral-color-filters`).

Those changes tune **how recommendation strategies consume** colour labels.
`openspec/specs/same-color-strategy/` is a downstream **consumer** of the profile
this change produces — its successor in the pipeline, not its replacement. Delete
or supersede the analyzer and every colour strategy in the product loses its
input. The two concerns sit on opposite sides of the same seam and both remain
live.

## What Shipped

Shipped in commit `7a52cdc`, "Release v1.0.2: spectral color analysis, cohesion
control, lazy completion" (2026-06-14).

Verified on `main` at archive time:

| Deliverable | Location |
|---|---|
| Spectral analyzer module | `src/xfinaudio/audio/spectral_profile.py` |
| Pinned analysis dependency | `pyproject.toml:22` — `librosa>=0.10,<0.12` |
| Persistence column | `spectral_profile_json` in `src/xfinaudio/library/track_repository.py` (upsert at `:50`, `:65-66`) |
| Scoring weight | `spectral: float = 0.10` — `src/xfinaudio/recommendation/scoring.py:29` |
| Scoring component | `_score_spectral` — `src/xfinaudio/recommendation/scoring.py:325`, applied at `:195` |
| Colour badge helper | `_format_spectral_color` — `src/xfinaudio/desktop/rendering.py:57` |
| Synthetic fixtures | `assets/synthetic_color_tests/` — `red_100hz.wav`, `green_500hz.wav`, `blue_8000hz.wav`, `highmid_2000hz.wav`, `green_blue_mix.wav` |

### Schema version — stated precisely

`src/xfinaudio/library/track_repository.py:20` currently reads
`SCHEMA_VERSION = 4`. **This change did not ship version 4.** Its own
`verify-report.md` records schema **v3** and a `v1 → v3` migration test. The bump
to 4 came later, in commit `01df174` (`perf(library): keep only parsed tags in
raw_metadata`), which is unrelated to spectral work.

What this change owns is the `spectral_profile_json` column and its round-trip,
not the current version number. The distinction is recorded rather than smoothed
over.

The change's `tasks.md` (Task 3) says "Bump `SCHEMA_VERSION` to 2" while the
verify report evidences v3 — the plan was written against an earlier baseline and
the implementation landed on v3. Historical text left as-is.

## Task History Contradiction — Annotated, Not Rewritten

**All 10 task groups in `tasks.md` are unchecked** (`[ ]`), yet this change's own
`verify-report.md` records `uv run pytest -q` — **769 tests PASS**, full gate
green, and "## Outstanding work — None. Task 8 is merged."

The code demonstrably shipped: every artifact in the What Shipped table above was
verified present on `main` while writing this report.

**The task history is deliberately left unchecked.** Ticking those boxes now
would fabricate a per-task TDD record that no evidence supports, and this
project's own governance forbids rewriting archived history during
reconciliation. The change's `apply-progress.md` already states this position
explicitly:

> `state.yaml` and `verify-report.md` record the change as completed and
> verified. The unchecked legacy task list conflicts with those artifacts, so
> this reconciliation does not rewrite task history or invent per-task TDD
> evidence.

This archive report takes the same line. The verification evidence is the
authoritative record of what shipped; `tasks.md` is an unmaintained plan.

## Verification Verdict

**PASS** — recorded in `verify-report.md`.

- `uv run pytest -q` — 769 tests passed
- `uv run pyright src tests` — 0 errors, 0 warnings, 0 informations
- `uv run pytest --cov --cov-fail-under=70 -q` — 89.21% coverage
- `uv run ruff check .` / `ruff format --check .` — PASS
- `uv run python scripts/release_gate_check.py --run` — PASS, all gates
- Release evidence regenerated via `scripts/render_release_gate_evidence.py`

16 requirement rows trace to named tests across
`tests/audio/test_spectral_profile.py`, `tests/audio/test_batch_analyzer.py`,
`tests/test_track_repository.py`, `tests/test_transition_scoring.py`,
`tests/test_recommendation_quality.py` and `tests/test_scan_service.py`.

### Performance work (Task 8)

Benchmarked over 20 synthetic 60-second WAVs; data retained in
`optimization-benchmark.json` / `optimization-benchmark.md`:

| Config | Median s | Throughput | Speedup |
|---|---|---|---|
| sequential | 1.110 | 18.02/s | 1.00× |
| parallel (`ProcessPoolExecutor`) | 0.414 | 48.31/s | 2.68× |
| thread (`ThreadPoolExecutor`) | 0.485 | 41.23/s | 2.29× |
| cached-rescan | 0.000 | 383,233/s | ~21,000× |

Thread executor chosen as default (avoids macOS spawn overhead and PyInstaller
pickling risk); native extension rejected, aggressive downsampling deferred.

## Scope Safety

Recorded in `verify-report.md` and still true: no audio file mutation, no
BPM/key/beatgrid detection, no real-time analysis during playback, no Serato
Database V2 writes. Analyzer failures degrade to `spectral_profile=None`.

This matters for `AGENTS.md` "No DSP scope": the analyzer performs **offline,
read-only** spectral classification for decision support. It does not detect
BPM or key, does not beat-track, and does not render, mix, time-stretch or
pitch-shift.

## Specs Synced

**No.** This change carries `spec.md` but has no `specs/` delta directory, and no
durable capability spec is created or updated by this archive pass. Archiving
here is a lifecycle-record correction only, with no production change.

The durable colour specs that exist —
`openspec/specs/same-color-strategy/` and
`openspec/specs/same-color-energy-strategy/` — describe strategy behaviour
downstream of this analyzer, not the analyzer itself.

## Archive Contents

- [x] `proposal.md` — intent and scope
- [x] `spec.md` — requirement scenarios
- [x] `design.md` — analyzer and persistence design
- [x] `tasks.md` — 10 task groups, all unchecked (see annotation above)
- [x] `apply-progress.md` — reconciliation note declining to rewrite task history
- [x] `verify-report.md` — full gate, 16 requirement rows, benchmark table
- [x] `optimization-benchmark.json`, `optimization-benchmark.md` — Task 8 data
- [x] `state.yaml` — rewritten to `gentle-ai.sdd-state.v1` (see above)

## Follow-Up Items

**(a) `tasks.md` never reconciled (OPEN, documentation).** Deliberately left. Any
future reconciliation must work from commit evidence, not from assumption, and
must not silently tick boxes.

## Archive Metadata

- **Created**: 2026-06-14
- **Updated**: 2026-06-14
- **Shipped**: 2026-06-14 (`7a52cdc`, v1.0.2)
- **Artifacts last touched**: 2026-07-18 (`43e879f`, reconciliation pass)
- **Archived**: 2026-08-08

**SDD Cycle Status**: COMPLETE — implemented, verified and archived, with the
`tasks.md` contradiction documented rather than resolved. Spec fold-in not
applicable (see Specs Synced).
