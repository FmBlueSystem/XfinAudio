# Review remediation of the 2.3.0 candidate

## Intent and problem

An evidence-based review of the 2.3.0 source candidate on `feat/ai-playlist-improvement`
(`3172b4f`) was asked to "revisa el proyecto" and then to resolve every finding
autonomously, run the tests and open the app. The review produced ranked, source-anchored
findings; this change is the record of fixing them.

The defects share one property: each is a *stale or unguarded statement about the current
tree*, not a missing feature. A shipped wheel force-included Qt Linguist catalogs that
nothing reads, a documentation set still taught a `uv run xfinaudio` launcher that was
never declared, a headless requirements snapshot had drifted from `uv.lock`, a Python
module still held a second connection-probe state machine from the retired Qt dialog, and
the optional-AI renderer could replace the request text of an in-flight paid call. The
deterministic core itself was already correct in the two places where the review suspected
missing behavior (playlist improvement save, AI transport privacy); those became guards
and one end-to-end integration test rather than rewrites.

## Ranked findings and disposition

| # | Finding | Disposition |
|---|---------|-------------|
| 1 | `playlist_file_export` accepted an export name that could leave the export folder | fixed (W1) + guard |
| 2 | The optional-AI renderer replaced the staged request text while a paid `ask` was in flight | fixed (W2) + guard |
| 3 | `desktop-electron/requirements-headless.txt` had drifted from `uv.lock`; the `.in` file it came from was not reproducible, and the compiled `packaging/linux/requirements-build.txt` the freezer lane installs had drifted from both | fixed (W3) + guards, including the regenerated freezer lock |
| 4 | Shipped documents referenced removed paths, a removed launcher and a removed translation workflow | fixed (W4) + guard |
| 5 | Malformed profile JSON became a silent "never analysed" track; a bad MD5 read was silent | fixed (W5) + guard |
| 6 | `openspec/config.yaml` and the SDD skill described the removed Qt stack | fixed (W6) + guards |
| 7 | Qt residue still shipped or still ran: translation catalogs, `QT_QPA_PLATFORM` workflow env, a dead probe state machine, stale `desktop/` bytecode, Qt vocabulary in the AI document | fixed (W7) + guards |
| 8 | The renderer's improvement save path was only covered against a stub bridge | fixed (W8): real-core integration test |
| 9 | 62 changes sit at `status: verify` and are never archived | reported, not fixed |
| 10 | Oversized modules (`playlist_service.py` 1651, `track_repository.py` 1037, `optimizer.py` 1034 lines) and copy-pasted renderer host boilerplate | reported, not fixed |
| 11 | Duplicated validation constants (`2..80` three times, 64-hex digest regex eight times) | reported, not fixed |

Items 9-11 are refactors with no defect to observe: they need their own change, their own
RED, and a review budget that a bug-fix pass cannot provide. They are listed so the next
session does not have to rediscover them.

## Review budget

The authored diff is 2 324 added and 5 417 deleted lines across 63 files, well over the
advisory 400-line budget, because it is ten independent findings rather than one. A single
review is therefore not requested; the work units below are each reviewable alone, and they
were developed in that order. **`design.md` D10 is the measured per-unit plan**: a table with
each unit's file count and line counts, the units that can be reviewed in isolation, and the
explicit statement that chained PRs are not recommended and why.

`W1` export containment → `W2` renderer request immutability → `W3` headless lock →
`W4` documentation freshness → `W5` observability → `W6` SDD state → `W7` Qt residue →
`W8` integration coverage → `W9` this record → `W10` gate and app launch.

Deletions dominate the diff (the Qt translation catalogs alone are 5k lines of generated
`.ts`), which the review budget does not count as authored reasoning.

## What this change does not do

- No audio mutation, no DSP, no live Serato DB V2 write, no `AppState` mutation.
- No production behavior change beyond the two fixes in W1 and W2; every other W-item is a
  documentation, packaging, observability or deletion change, guarded by a test.
- No live provider call, no credential read, no network access, no real-library access.
- No push, tag, merge or release. The corrections are nine local work-unit commits on
  `feat/ai-playlist-improvement`, and the final report states that explicitly.
