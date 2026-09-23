# Design: arc-subset-sequencing

Status: implemented per frozen spec SPEC-WU25 (three adversarial review rounds; the
decision was already made — implement it, do not revisit).

## 1. The design contract

A new path-construction primitive in `optimizer.py` that **selects** a subset of length
`arc_length` from the full `_bpm_reachable_from`-filtered pool, rooted at the anchor (or
the last manual-prefix track as an external root), respecting `end_path` as a hard
terminal constraint, maximizing transition score plus per-slot arc adherence, subject to
every edge satisfying `max_bpm_difference_percent`. The pool is never pre-truncated with
`_shortlist_for_sequencing` before this primitive.

## 2. The routing branch

`recommend_sequence` routes to `_arc_subset_recommendation` when
`arc_strategy is not None and max_bpm_difference_percent is not None and arc_length is not None`.

Deviation note (recorded, not hidden): the frozen spec states the branch condition as
`arc_strategy is not None and max_bpm_difference_percent is not None`. The implementation
adds `arc_length is not None` so the spec's required explicit behaviour for
`arc_length is None` is a **defined fallback to the legacy solvers** (`exact` /
`greedy-2opt`), asserted by
`test_hard_arc_defines_none_start_missing_bpm_and_uncapped_fallback`. In practice
`playlist_service.py` always sizes `arc_length` for arc strategies, so the reachable call
shape is unchanged.

## 3. Hybrid exact/beam solver

- **Exact** (`_exact_arc_subset_path`, optimizer name `arc-subset-exact`): target-length
  bitmask DP in the style of `_exact_path`, but stopping at `target` placements instead
  of requiring `full_mask`. Used when the feasible search domain is `<= exact_limit`.
- **Beam** (`_beam_arc_subset_path`, optimizer name `arc-subset-beam`): deterministic
  beam search (default width 64) otherwise, with stable tie-breaking on
  `(score, canonical path key)` — never raw dict/set iteration order. On failure with
  budget exhausted and a small capped domain (≤ 128), one widened retry (width up to
  16,384) runs before reporting failure.
- Both solvers are exercised and asserted (`test_hard_arc_exact_and_beam_paths_are_
  deterministic_and_observable`); repeat runs are deterministic.

## 4. Lazy scoring — no eager matrices

`_score_matrix` and `_arc_bonuses` are never called on the reachable pool. Transitions
are computed per explored edge through an LRU-cached `transition()` closure over
`score_transition`; arc adherence comes from `_lazy_arc_bonus`, computed per
`(candidate, slot)` on demand. The arc-bonus **normalization domain** is the actually
feasible search domain (reachable within remaining hops and compatible with mandatory
controls and a fixed end), not the raw pool — normalizing against unreachable tracks
would stretch the scale and weaken every real candidate's bonus
(`test_small_arc_domain_does_not_hide_a_low_arc_bonus_connector`). Exploration does not
retain full `TransitionScore` objects in the caller's cache — only the final path's
edges are cached (`test_hard_arc_exploration_only_caches_the_final_path_edges`).

## 5. Pool sizing — feasibility-aware, never blind truncation

No fixed pre-search cap. Feasibility pruning is algorithmic: `_lazy_bpm_neighbors`
restricts discovery to BPM-neighbor windows (including folded 2:1 windows), and
`_reachable_indices` / hop-distance maps bound the search domain by remaining hops
against `target` (and, when `end_path` is fixed, by `hops_from_start[i] +
hops_to_end[i] <= target - 1`). Domain sizes below `target` are reported as **proven
infeasible** with the exact count. The numeric exploration budget (beam width) is
calibrated, not the selection method.

## 6. Mandatory-path handling — fail closed

Locked paths, the manual-order prefix seam, `start_path`, and `end_path`
(`preserved_control_paths`, `controls.py`) must all appear in the selected subset or the
call fails closed with an explicit warning; a locked or manually-ordered track is never
silently dropped. Defined behaviours, each tested:

| Case | Behaviour | Test |
|---|---|---|
| Mandatory path not in pool | Empty result, proven-infeasible warning | `test_hard_arc_reports_a_mandatory_path_missing_from_the_pool` |
| Mandatory count exceeds target | Empty result, proven-infeasible warning | `test_hard_arc_fails_closed_when_mandatory_paths_exceed_target` |
| Mandatory paths cannot coexist in one BPM-valid path | Empty result, explicit warning | `test_hard_arc_fails_closed_when_mandatory_paths_cannot_coexist` |
| Locked paths + manual seam | Always present; seam is an external root, never selected twice | `test_hard_arc_keeps_locked_paths_and_uses_manual_seam_as_external_root` |
| `start_path == end_path`, one-track target | That single track is the result | `test_hard_arc_one_track_can_be_both_start_and_end` |

## 7. Manual-prefix accounting

`playlist_service.py` strips the manual prefix before optimization and sets
`start_path = None` when the prefix is non-empty. The integration threads:

- `target_length` = requested arc length − manual-prefix length (clamped at 0 and at the
  pool size), computed by `_expected_arc_subset_length` from played-slot durations — the
  arc shape describes the **whole** set the DJ plays, per the existing `arc_length`
  contract (unchanged);
- `arc_slot_offset` = manual-prefix length;
- `external_start` = the last manual-prefix track, used as the transition root and never
  selectable.

## 8. `end_path` reserved, not raced for

`end_path` is mandatory and reserved for the terminal slot. Minimum-hops-to-`end_path`
is a pruning signal during search (`_hop_distances`), not an afterthought check. A
reachable end lands there (`test_hard_arc_reserves_a_reachable_end_for_the_terminal_
slot`); a genuinely unreachable end produces an explicit warning and never an illegal
edge (`test_hard_arc_reports_a_proven_unreachable_end`).

## 9. Proven-infeasible vs. budget-exhausted

Different outcomes, different warnings. Graph/hop reasoning (mandatory paths outside the
reachable domain, `len(reachable) < target`, `len(search_domain) < target`, fixed-end hop
budget violations) produces "Arc subset proven infeasible: …". A beam that ran out of
expansions without proof produces "Arc subset beam search budget exhausted without a full
path; this is not proof that none exists." The distinction is asserted
(`test_hard_arc_distinguishes_budget_exhaustion_from_proven_infeasibility`).

## 10. Folded 2:1 edge comparison — in scope; BPM reinterpretation — not

`_lazy_bpm_neighbors` queries BPM windows near `b`, `b/2`, and `2b` (window margin derived
from the ceiling), validated through the existing `bpm_difference_percent`, so neighbor
discovery never silently omits edges the rest of the app already accepts
(`test_hard_arc_neighbor_discovery_includes_folded_two_to_one_edges`). This is **edge
comparison only**. Parsing, storing, or correcting *declared, scanned* BPM is out of
scope — see §12. A candidate with unknown/missing BPM passes through as compatible
(`_edge_is_playable`), consistent with the existing scoring and final gate
(`test_hard_arc_defines_none_start_missing_bpm_and_uncapped_fallback`).

## 11. Why the legacy paths are deliberately untouched

`_exact_path`, `_heuristic_path`, `_score_matrix`, `_arc_bonuses`, and
`UNPLAYABLE_TRANSITION_PENALTY` keep serving every other call shape exactly as today:
every call that does not set both `arc_strategy` and `max_bpm_difference_percent` takes
the original path, pinned by `test_non_hard_arc_call_shapes_keep_the_legacy_solvers` and
the pre-existing `test_recommend_sequence_*` suite. In `playlist_service.py`, only the
arc branch skips `_shortlist_for_sequencing`; every other caller is unaffected
(`test_non_arc_strategy_does_not_route_through_subset_search`,
`test_chill_keeps_its_sort`).

## 12. Explicitly out of scope

- **BPM metadata parsing or correction** (half-time/double-time correction of declared,
  scanned BPM). This repo has a documented incident: a half-time correction attempt
  doubled 1,297 real BPMs (Calvin Harris 128→256, Elvis 125→250) due to circular
  validation, and was reverted. Stored BPM values are never reinterpreted under any
  framing.
- `_bpm_reachable_from`'s own reachability algorithm.
- `chill` or any non-arc strategy.
- `MAX_ADJACENT_BPM_DIFFERENCE_PERCENT`, `UNPLAYABLE_TRANSITION_PENALTY`, or any existing
  threshold.
- `energy_arc.py`'s shape functions.

## 13. Dissent/decision log

None. SPEC-WU25 froze the decision after three adversarial review rounds and records no
open dissent to carry forward.
