# Proposal: arc-subset-sequencing

## Why

The four energy-arc playlist strategies (`harmonic_journey`, `warmup`, `build`,
`peak_time` — every strategy where `energy_arc.py::traces_an_arc` is true) collapse on
real libraries. The optimizer branch in `recommend_playlist` feeds each arc a shortlist
produced by `_shortlist_for_sequencing`, which truncates the BPM-reachable set **in
original arrival order** — an order with no relationship to BPM adjacency. The resulting
shortlist is BPM-fragmented into disconnected components, and no permutation of it is
fully playable: `_exact_path` and `_heuristic_path` order everything they receive and
cannot leave a bad candidate out.

Measured baseline (frozen spec SPEC-WU25, three independent verification rounds, real
10,607-track library): for one real anchor, 4,236 candidates survive the energy-range
filter, 4,230 remain BPM-reachable from the anchor, 48 enter `_shortlist_for_sequencing`
(limit `max(30, target_count*4)`), and only **2** survive the final
`_drop_generated_tracks_after_impossible_bpm_jumps` gate — the 48-item shortlist's
BPM-compatible subgraph has 6 disconnected components.

Aggregate baseline across 40 real anchors per strategy, `target_count=12` (pre-change
numbers from SPEC-WU25; NOT re-measured for this change — see `verify-report.md`):

| Strategy | Desktop-capped pool (real UI path) | Raw library input |
|---|---|---|
| harmonic_journey | mean 12.00, 40/40 full | mean 9.40, 13/40 full |
| warmup | mean 11.675, 38/40 full | mean 3.825, 3/40 full |
| build | mean 11.775, 38/40 full | mean 2.80, 3/40 full |
| peak_time | mean 11.95, 39/40 full | mean 4.725, 1/40 full |

The desktop app currently masks most of this via `plan_recommendation_candidates` pool
surplus, but does not fix it; the defect resurfaces for atypical anchors, sparser energy
bands, and smaller libraries. `chill` is unaffected (its `_low_and_flat` shape is not an
arc).

## What Changes

Add a new path-construction primitive in `optimizer.py` (`_arc_subset_recommendation`
with `_exact_arc_subset_path` / `_beam_arc_subset_path`) that **selects** a subset of
length `arc_length` from the full BPM-reachable pool, instead of permuting a
pre-truncated shortlist:

1. Hybrid exact bitmask DP / deterministic beam search, routed by a tractability limit,
   both exercised by tests.
2. Lazy scoring — per-edge `score_transition` and per-slot arc adherence on demand; no
   `pool × pool` or `pool × slot` matrix is ever materialized.
3. Pool sizing that never blind-truncates: feasibility-aware pruning (BPM-neighbor
   windows, hop-budget reasoning) instead of a flat front-N cut.
4. Mandatory-path handling that fails closed: locked paths, the manual-order prefix seam
   (as an external root), `start_path`, and `end_path` always survive or the call returns
   an explicit warning — never a silently dropped control.
5. Folded 2:1 BPM edge comparison in neighbor discovery (60↔120-style pairs validated
   through the existing `bpm_difference_percent`), without touching stored BPM values.
6. Distinct, honest warnings for proven-infeasible vs. budget-exhausted searches.
7. `playlist_service.py` routes arc strategies through the new primitive (branch:
   arc strategy + BPM ceiling + sized arc length) and stops pre-truncating via
   `_shortlist_for_sequencing` for that branch only; `_expected_arc_subset_length` sizes
   the arc by the played slot, and manual-prefix accounting threads target length, slot
   offset, and the external root.

## Capabilities

### Modified: energy-arc-sequencing

Subset selection and ordering for the four energy-arc playlist strategies, replacing
shortlist-then-permute with feasible-subset construction.

## Impact

- **Modified surfaces**: `src/xfinaudio/recommendation/optimizer.py`,
  `src/xfinaudio/recommendation/playlist_service.py`,
  `tests/test_sequence_optimizer.py`, `tests/test_playlist_service.py` — 999 insertions,
  10 deletions.
- **Untouched by design**: `_exact_path`, `_heuristic_path`, `_score_matrix`,
  `_arc_bonuses`, `UNPLAYABLE_TRANSITION_PENALTY`, every threshold, `_bpm_reachable_from`
  itself, non-arc strategies (`chill` included), and `energy_arc.py` shape functions.
- **Review budget (400 lines, per AGENTS.md)**: this change is 999 insertions (10
deletions) — 2.5×
  the budget. Per AGENTS.md this requires either a chained-PR plan or an explicit,
  recorded accept decision. **No such decision is recorded yet**; this is tracked as an
  open item in `tasks.md`. The single-write-thread port provenance (one logical rescue
  from a stale branch) and the shared test seam between primitive and service argue for
  one review slice, but the accept is the maintainer's call, not this document's.

## Decision provenance

The specification (SPEC-WU25, Batch 19) was frozen after **three adversarial review
rounds** and was already reviewed before implementation. Every design property in
`design.md` closes a specific gap found in those reviews (lazy scoring, hybrid solver,
proven-infeasible honesty, mandatory-control survival, folded edges, domain-aware arc
normalization, pool sizing, determinism). This change implements that frozen decision;
it does not revisit it.
