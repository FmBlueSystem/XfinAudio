# ODD feature ledger — arc-subset-sequencing

**Branch:** `feat/arc-subset-sequencing` (created from `main` @ `490f79a`)
**Worktree:** `~/Desktop/XfinAudio/repo` — this ledger was first written in a temporary worktree
under `~/orca/workspaces/`, which the 2026-09-22 consolidation deleted.
**Frozen spec (input):** `SPEC-WU25.md` in the primary clone (local-only file, excluded via
`.git/info/exclude`; Batch 19 / WU25, three adversarial review rounds, frozen)
**Raw pickaxe target:** 400 lines of changed source per review budget (`AGENTS.md`)
**Runtime:** macOS, Python 3.11, `uv`

## Why this branch exists

The primary clone — a local checkout outside this consolidated folder, since deleted — sat on
`feat/library-file-watcher-integration` at `b2b1547`, **68 commits behind `main`**, with this
work uncommitted in its working tree. `main` already contains everything else that clone
carried (the EBU R128 loudness module merged as `6fabb3e` and its remediation chain, the
archived `library-file-watcher-rescan` change, the library table column-contract refactor
`490f79a`). Committing there would have landed this work on a stale base.

The two files whose base was identical in `HEAD` and `main`
(`recommendation/optimizer.py`, `tests/test_sequence_optimizer.py`) were ported with an exact
`git apply`; the two whose base had moved
(`recommendation/playlist_service.py`, `tests/test_playlist_service.py`, because `main` added
the loudness band filter) were ported with `git apply -3` and merged textually with `main`'s
loudness additions. Verified faithful: the port reproduces **999 insertions**, identical to
the original working-tree delta, and the optimizer + its test file are byte-identical to the
source WIP.

## The defect this fixes

`tests`-verified root cause (traced in the frozen spec): for the four energy-arc strategies
(`harmonic_journey`, `warmup`, `build`, `peak_time` — `traces_an_arc(name) is True`),
`_shortlist_for_sequencing` truncates a BPM-reachability set returned in **arrival order**, so
a 48-item shortlist can contain 6 disconnected BPM components. No permutation of a fragmented
graph is playable, regardless of optimizer quality: the old path ordered *every* track it was
handed, then a downstream gate dropped whatever it could not reorder.

Baseline measured over 40 real anchors, `target_count=12` (raw library input):

| strategy | mean length | full sets |
|---|---|---|
| harmonic_journey | 9.40 | 13/40 |
| warmup | 3.825 | 3/40 |
| build | 2.80 | 3/40 |
| peak_time | 4.725 | 1/40 |

## Tasks

- [x] 1. Port the 4 files onto a branch from `main`; verify the port is faithful
- [x] 2. Author the OpenSpec change artifacts (`openspec/changes/arc-subset-sequencing/`)
- [x] 3. Work-unit commit: the optimizer primitive
- [x] 4. Work-unit commit: the playlist_service routing + pool sizing
- [x] 5. Work-unit commit: the OpenSpec artifacts
- [x] 6. Re-run the aggregate 40-anchor measurement and record before/after
- [x] 7. Full gate + release gate + evidence report

## Evidence so far

Focused (worktree, `feat/arc-subset-sequencing`):

```
uv run pytest tests/test_sequence_optimizer.py tests/test_playlist_service.py -q
241 passed in 3.51s
```

Full gate (worktree, macOS, Python 3.11):

```
uv run pytest -q
1901 passed, 45 warnings in 77.13s

uv run pytest --cov --cov-fail-under=70 -q
TOTAL 11622 statements  978 missed  91.58%
1901 passed

uv run pyright src tests
0 errors, 0 warnings, 0 informations

uv run ruff check .
All checks passed!

uv run ruff format --check .
309 files already formatted
```

## Commits

All on `feat/arc-subset-sequencing`. Nothing pushed; no commit on `main`.

| Work unit | Commit | Note |
|---|---|---|
| WU1 optimizer primitive | `04eeace` | `optimizer.py` +622/−2, `tests/test_sequence_optimizer.py` +250; green in isolation (34 passed) |
| WU2 service routing | `b0c25fa` | `playlist_service.py` +53/−8, `tests/test_playlist_service.py` +74; focused 241 passed |
| WU3 governance | `3245943` | the seven OpenSpec artifacts + this ledger |
| WU4 verification | `5317494` | added `scripts/arc_subset_benchmark.py` (the repeatable 40-anchor harness) plus the before/after, cost and re-scope evidence in `openspec/changes/arc-subset-sequencing/` |
| WU3b evidence recording | `0e11333` | recorded the work-unit commits and the final gate evidence in the report and this ledger |
| WU5 ledger bookkeeping | the commit that carries this row | filled the WU4 hash and corrected the `Worktree` field above, which pointed at a deleted directory. A commit cannot record its own hash, so this row names the work unit by its content. The table lists every substantive work unit; later bookkeeping edits to this ledger are named rather than numbered, for the same reason. |

The `0e11333` row above was missing until this edit: the table listed four of the branch's five
commits. It was found by diffing the table against `git log`, which is the check that catches
this class of gap — not by reading the table.

## Final gate at the tip (`3245943` plus the evidence commit)

Full `AGENTS.md` verification sequence, macOS, Python 3.11:

```
uv run pytest -q                                    1901 passed in 64.23s
uv run pyright src tests                            0 errors, 0 warnings, 0 informations
uv run pytest --cov --cov-fail-under=70 -q          91.58% (11622 stmts, 978 missed)
uv run ruff check .                                 All checks passed!
uv run ruff format --check .                        309 files already formatted
uv run python scripts/release_gate_check.py --run    exit 0, every gate PASS
```

The release gate ran the publication-docs, publication-artifact-hygiene, source-package-hygiene
(sdist + wheel inspected) and PyInstaller check-only gates, plus root artifact hygiene.
`real Mixed In Key audio QA` reports COMPLETED. Working tree clean afterwards.

## Open risks

- ~~The frozen spec's PROOF section also requires the aggregate 40-anchor before/after table
  against a **scratch copy** of `~/.xfinaudio/xfinaudio.sqlite3` (never the live DB).~~ **Done.**
  Ran against a scratch copy, 40 anchors, `target_count=12`, both pool conditions. Raw: 3-10 of
  40 full sets before, 40 of 40 after. Desktop: `peak_time` 33 of 40 before, 39 after.
- ~~The spec's baseline table came from a real 10,607-track library; the improvement must be
  re-measured, not assumed.~~ **Done, with a caveat.** Re-measured on the real library (10,511
  complete tracks on this machine). The harness was first validated by running it on `main` and
  checking it against the recorded baseline, which it reproduces in shape and, in the desktop
  condition, almost exactly. The anchor set itself is a documented replacement, because the
  spec's is lost.
- **New, and unmeasured before this pass: the change costs more.** 4.7x total, up to 13.7x in
  the raw condition. The UI path — the one a DJ feels — stays at or under 0.54s per
  recommendation including pool planning. Recorded in `verify-report.md`.
- **SPEC-WU25 is unrecoverable.** It was a local-only file in the clone the consolidation
  deleted, and it is in no ref of this repository. Task 6.2 could not be completed as written
  and was re-scoped; that weaker claim is stated in `verify-report.md`.
- Review budget: this change is ~999 changed lines, above the 400-line `AGENTS.md` budget; it
  needs either an explicit chained-PR plan or a recorded accept decision.
