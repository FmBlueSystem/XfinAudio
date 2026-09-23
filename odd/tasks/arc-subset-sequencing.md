# ODD feature ledger — arc-subset-sequencing

**Branch:** `feat/arc-subset-sequencing` (created from `main` @ `490f79a`)
**Worktree:** `/Users/freddymolina/orca/workspaces/xfinaudio-local-main/arc-subset-sequencing`
**Frozen spec (input):** `SPEC-WU25.md` in the primary clone (local-only file, excluded via
`.git/info/exclude`; Batch 19 / WU25, three adversarial review rounds, frozen)
**Raw pickaxe target:** 400 lines of changed source per review budget (`AGENTS.md`)
**Runtime:** macOS, Python 3.11, `uv`

## Why this branch exists

The primary clone `/Users/freddymolina/Documents/xfinaudio-local-main` sits on
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
- [ ] 2. Author the OpenSpec change artifacts (`openspec/changes/arc-subset-sequencing/`)
- [ ] 3. Work-unit commit: the optimizer primitive
- [ ] 4. Work-unit commit: the playlist_service routing + pool sizing
- [ ] 5. Work-unit commit: the OpenSpec artifacts
- [ ] 6. Re-run the aggregate 40-anchor measurement and record before/after
- [ ] 7. Full gate + release gate + evidence report

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

| Work unit | Commit | Note |
|---|---|---|
| _pending_ | | |

## Open risks

- The frozen spec's PROOF section also requires the aggregate 40-anchor before/after table
  against a **scratch copy** of `~/.xfinaudio/xfinaudio.sqlite3` (never the live DB). Not yet run.
- The spec's baseline table came from a real 10,607-track library; the improvement must be
  re-measured, not assumed.
- Review budget: this change is ~999 changed lines, above the 400-line `AGENTS.md` budget; it
  needs either an explicit chained-PR plan or a recorded accept decision.
