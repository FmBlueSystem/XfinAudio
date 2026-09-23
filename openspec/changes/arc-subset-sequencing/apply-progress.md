# Apply Progress: arc-subset-sequencing

## Status

Implementation and tests are applied on `feat/arc-subset-sequencing` and locally
validated (see `verify-report.md`). Aggregate re-measurement and independent
verification are pending.

## What was applied

| File | Change |
|---|---|
| `src/xfinaudio/recommendation/optimizer.py` | New arc-subset primitive: `_arc_subset_recommendation`, `_exact_arc_subset_path`, `_beam_arc_subset_path`, `_lazy_bpm_neighbors`, `_lazy_arc_bonus`, `_reachable_indices`, `_hop_distances`, `_subset_initial_indexes`, `_edge_is_playable`, `_empty_subset_result`; `recommend_sequence` routing branch. Legacy `_exact_path`/`_heuristic_path`/`_score_matrix`/`_arc_bonuses` untouched. (+622, −2) |
| `src/xfinaudio/recommendation/playlist_service.py` | Arc branch skips `_shortlist_for_sequencing`; new `_expected_arc_subset_length`; threads `target_length`, `mandatory_paths`, `external_start`, `arc_slot_offset`; propagates subset warnings. (+53, −8) |
| `tests/test_sequence_optimizer.py` | 18 new test functions covering SPEC-WU25 optimizer test items 1–10. (+250) |
| `tests/test_playlist_service.py` | End-to-end tests: raw vs. desktop-capped pool per strategy, non-arc bypass, control preservation, slot sizing. (+74) |

Total: 999 insertions, 10 deletions (`git diff HEAD --stat`).

## Port provenance

This work was rescued from the stale branch `feat/library-file-watcher-integration` in
`/Users/freddymolina/Documents/xfinaudio-local-main`, where it sat uncommitted with that
branch 68 commits behind `main`. The four files were ported onto
`feat/arc-subset-sequencing` (based on `main`): two byte-identically via `git apply`,
two via 3-way merge because `main` had independently added the loudness band filter to
`playlist_service.py` in the meantime. The port reproduces exactly 999 insertions.

## TDD evidence

Strict TDD was mandated by SPEC-WU25 and the tests were written first in the original
rescued work. **This writer did not observe the RED runs** (the implementation predates
this documentation task), so RED evidence is reported as inherited, not observed:

- RED: inherited — SPEC-WU25 required tests-first with seen red; the rescued test block
  (`test_energy_arc_does_not_collapse_on_a_fragmented_shortlist` and the
  `test_hard_arc_*` family) predates the port. The original RED observations are not
  reproducible from this worktree's history and are recorded here as provenance, not
  fresh evidence.
- GREEN: `uv run pytest tests/test_sequence_optimizer.py tests/test_playlist_service.py -q`
  → 241 passed in 3.51s (parent-session measurement, `verify-report.md`).

## PROOF deviation (recorded honestly)

The frozen spec's PROOF section asks for full-output `uv run pytest -q && uv run ruff
check . && uv run ruff format --check .` **plus** the aggregate re-measurement (40 real
anchors, all four strategies, desktop-capped and raw conditions) against a scratch copy
of the SQLite library (never the live DB).

- The three commands were run and passed on this branch — evidence recorded verbatim in
  `verify-report.md`.
- **The aggregate 40-anchor re-measurement has NOT been run.** The before/after table is
  therefore not available; only the frozen spec's pre-change baseline exists. Tracked as
  open task 6.1.

## Scope notes

- No library audio or database was touched by this task; the aggregate measurement, when
  run, must use a scratch copy of the SQLite library.
- The legacy optimizer paths and every threshold are unchanged, per design §11–§12.
