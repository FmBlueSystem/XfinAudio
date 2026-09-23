# Verify Report: arc-subset-sequencing

**Change**: arc-subset-sequencing
**Status**: verification complete; one item is left to the owner (task 6.4, the review-budget
disposition).
**Commit range under test**: `490f79a..3245943` on `feat/arc-subset-sequencing`
(`04eeace` optimizer primitive, `b0c25fa` service routing, `3245943` governance), plus the
verification work unit that added `scripts/arc_subset_benchmark.py` and this report.

## Independent verification (task 6.3)

The "Measured evidence" block at the end of this report was measured by the session that
implemented this change. It was re-measured on 2026-09-23 by a different session, on the same
branch and machine, and it reproduces:

| Command | Implementing session | Independent re-measurement |
|---|---|---|
| `uv run pytest -q` | 1901 passed, 77.13s | 1901 passed, 65.19s |
| `uv run pytest --cov -q` | 91.58%, 11622 statements | 91.58%; floor 70 reached |
| `uv run pyright src tests` | 0 errors, 0 warnings | 0 errors, 0 warnings, 0 informations |
| `uv run ruff check .` | All checks passed! | clean |
| `uv run ruff format --check .` | 309 files | as recorded at that revision |

The change's own spec delta names 22 distinct pinning tests by file and function. All 22 exist
in the tree, and a run selecting the `hard_arc` / `arc_subset` / fragmented / legacy /
small-domain cases passes 21 of them within a 241-test run of the two files that hold them.

**This is verification, not review.** Running the gates and the measurement myself is
independent verification of the claims. It is not a native review transaction, and this report
claims no review receipt; `state.yaml` keeps `review_status: pending`.

## Aggregate 40-anchor measurement (task 6.1)

The frozen spec's own anchor set is unrecoverable — see "Why task 6.2 changed shape". This
measurement therefore defines its own, in the open: **40 anchors evenly spaced across the
library ordered by path**, drawn from the 10,511 complete tracks of a **scratch copy** of the
real application database (`~/.xfinaudio/xfinaudio.sqlite3` was never read directly).
`target_count=12`. The harness is `scripts/arc_subset_benchmark.py`.

### The harness was first checked against the recorded baseline

Before measuring the branch, the same harness was run on `main`, to test it against the
pre-change table recorded in `proposal.md`:

| strategy | recorded (raw) | measured on `main` (raw) | recorded (desktop) | measured on `main` (desktop) |
|---|---|---|---|---|
| harmonic_journey | 9.40, 13/40 | 9.175, 10/40 | 12.00, 40/40 | 12.00, 40/40 |
| warmup | 3.825, 3/40 | 3.475, 3/40 | 11.675, 38/40 | 11.925, 39/40 |
| build | 2.80, 3/40 | 3.5, 3/40 | 11.775, 38/40 | 11.8, 39/40 |
| peak_time | 4.725, 1/40 | 5.3, 3/40 | 11.95, 39/40 | 10.65, 33/40 |

Same shape and same order of magnitude, and in the desktop condition several values land almost
exactly — `harmonic_journey` is identical at 12.00 and 40/40. The residual differences in the
raw condition are expected, because this anchor set is a documented replacement rather than the
spec's. Critically, **before and after use the same anchors**, so the delta below does not
depend on reproducing the lost set.

### Before and after

Raw library input — the condition this change exists to fix:

| strategy | before (mean, full) | after (mean, full) |
|---|---|---|
| harmonic_journey | 9.175, 10/40 | 12.0, 40/40 |
| warmup | 3.475, 3/40 | 12.0, 40/40 |
| build | 3.5, 3/40 | 12.0, 40/40 |
| peak_time | 5.3, 3/40 | 12.0, 40/40 |

Desktop-capped pool (the real UI path, 120 records):

| strategy | before (mean, full) | after (mean, full) |
|---|---|---|
| harmonic_journey | 12.0, 40/40 | 12.0, 40/40 |
| warmup | 11.925, 39/40 | 12.0, 40/40 |
| build | 11.8, 39/40 | 12.0, 40/40 |
| peak_time | 10.65, 33/40 | 11.7, 39/40 |

The defect is fixed in the condition it targets, and the desktop path — where the existing pool
surplus already masked most of it — gains the remainder: `peak_time` goes from 33 of 40 full
sets to 39.

### Cost

The change is slower, and this was never measured before. Same harness, same anchors:

| condition | strategy | before | after | factor |
|---|---|---:|---:|---:|
| raw | harmonic_journey | 7.11s | 97.13s | 13.7x |
| raw | warmup | 7.65s | 28.10s | 3.7x |
| raw | build | 8.67s | 97.13s | 11.2x |
| raw | peak_time | 5.00s | 58.67s | 11.7x |
| desktop | harmonic_journey | 13.30s | 13.05s | ~1.0x |
| desktop | warmup | 9.58s | 9.58s | 1.0x |
| desktop | build | 12.89s | 13.70s | 1.06x |
| desktop | peak_time | 8.54s | 21.52s | 2.5x |

Totals: 72.7s before, 338.9s after, 4.7x. The penalty lives in the raw condition, which is not
the UI path. Per recommendation in the desktop condition, pool planning included: 0.33s /
0.24s / 0.34s / 0.54s after, against 0.33s / 0.24s / 0.32s / 0.21s before. The worst case stays
under 0.6s for an interactive action. This is a result to weigh, not a blocker.

### What this measurement does not establish

1. The anchor set is a documented replacement, not the spec's.
2. The "desktop" condition replicates the **pool cap** (120 records, from `pool_size_for_slot`
   for a 30-minute slot) but not the desktop's full call signature:
   `target_duration_minutes` and `played_seconds_per_track` are not passed, only
   `target_count=12`. The recorded baseline table has the same limitation, so the comparison is
   like for like, but this is not "the exact desktop call".
3. Set lengths are counted, not musical quality. Nothing here substitutes for a human listen,
   or for the manual audio QA gate.
4. **One observation is unexplained.** In the desktop condition, `harmonic_journey`, `warmup`
   and `build` each emit `Dropped N generated track(s)` with **identical N per anchor** (13, 28,
   23, 18, 16, 33, 15, 24, ...), although those three do not share a pool: only
   `harmonic_journey` and `build` have identical pool membership, and `warmup` does not. Two
   hypotheses were tested and both were refuted by measurement (identical pools; identical
   per-strategy pools). The behaviour looks benign — the desktop path still returns 39-40 of 40
   full sets — but the mechanism is not understood, and it is recorded here rather than
   explained away.

## Why task 6.2 changed shape

Task 6.2 required the frozen spec's required-properties checklist (SPEC-WU25 test items 1-13)
to be confirmed item by item. That is no longer possible.

SPEC-WU25 was a local-only file: `SPEC-WU25.md` in the primary clone, excluded via
`.git/info/exclude`. The consolidation of 2026-09-22 deleted that clone. It is in no ref of
this repository — no commit adds or removes any `*SPEC-WU25*` path, and no `SPEC-*.md` is
versioned on any local or remote branch tracked here.

Faced with a lost document, the checklist was replaced with something checkable: this change's
own spec delta (`specs/energy-arc-sequencing/spec.md`) names a pinning test for every one of
its 15 scenarios, and all 22 distinct test names it cites exist and pass. That is a **weaker**
claim than confirming a frozen checklist, and it is the strongest claim the surviving artifacts
support. The loss is recorded so the gap is not mistaken for coverage.

## Outstanding

1. **Review-budget disposition (task 6.4)** — about 999 changed source lines against the
   400-line budget in `AGENTS.md`. Neither a chained-PR plan nor a recorded accept exists. This
   is the owner's decision and the only thing between this change and archive.
2. **A human listen.** See "What this measurement does not establish", point 3.

## Measured evidence (recorded by the implementing session)

```text
uv run pytest tests/test_sequence_optimizer.py tests/test_playlist_service.py -q
-> 241 passed in 3.51s

uv run pytest -q
-> 1901 passed, 45 warnings in 77.13s

uv run pytest --cov --cov-fail-under=70 -q
-> TOTAL 11622 statements, 978 missed, 91.58%
-> 1901 passed

uv run pyright src tests
-> 0 errors, 0 warnings, 0 informations

uv run ruff check .
-> All checks passed!

uv run ruff format --check .
-> 309 files already formatted

uv run python scripts/release_gate_check.py --run
-> exit 0; every gate PASS (publication docs, publication artifact hygiene, source
   package hygiene with sdist and wheel inspected, PyInstaller check-only, root
   artifact hygiene); working tree clean afterwards
```
