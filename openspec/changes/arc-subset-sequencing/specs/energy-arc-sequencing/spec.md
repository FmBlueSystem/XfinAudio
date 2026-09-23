# Spec Delta: energy-arc-sequencing

## ADDED Requirements

### Requirement: fragmentation-resistant arc subset selection

For every energy-arc strategy (`harmonic_journey`, `warmup`, `build`, `peak_time`), the
system SHALL construct the sequence by selecting a feasible subset of the full
BPM-reachable pool instead of permuting a pre-truncated shortlist, so the result no
longer depends on whether the pool arrived desktop-capped or raw.

#### Scenario: fragmented shortlist no longer collapses
- **GIVEN** a pool whose BPM-compatible subgraph is fragmented into disconnected
  components while the arc needs material at both energy extremes
- **WHEN** the arc strategy sequences it
- **THEN** a feasible full-length subset is returned instead of the shortlist-collapse
  outcome
  (`tests/test_sequence_optimizer.py::test_energy_arc_does_not_collapse_on_a_fragmented_shortlist`)

#### Scenario: raw and desktop-sized pools converge
- **GIVEN** the same effective library reachable through a raw pool and a desktop-capped
  pool
- **WHEN** each of the four arc strategies builds a playlist
- **THEN** both conditions return the full target count
  (`tests/test_playlist_service.py::test_arc_strategy_selects_the_same_full_set_from_raw_or_desktop_sized_pool`,
  parametrized over all four strategies)

### Requirement: BPM-valid transitions in every returned arc

Every adjacent pair in a returned arc path SHALL satisfy
`max_bpm_difference_percent`, with no exceptions.

#### Scenario: hard arc respects the ceiling on every edge
- **WHEN** an arc subset path is returned under a strict BPM ceiling
- **THEN** every adjacent pair satisfies the ceiling
  (`tests/test_sequence_optimizer.py::test_hard_arc_every_returned_edge_respects_the_bpm_ceiling`)

### Requirement: end_path as a reserved terminal constraint

A requested `end_path` SHALL be reserved for the terminal slot — never consumed early —
using minimum-hops reasoning during search.

#### Scenario: reachable end is landed on
- **WHEN** `end_path` is requested and reachable within the hop budget
- **THEN** the path terminates on `end_path`
  (`tests/test_sequence_optimizer.py::test_hard_arc_reserves_a_reachable_end_for_the_terminal_slot`)

#### Scenario: unreachable end is reported, never violated
- **WHEN** `end_path` is requested but genuinely unreachable given the pool
- **THEN** an explicit warning is returned and no illegal edge is produced
  (`tests/test_sequence_optimizer.py::test_hard_arc_reports_a_proven_unreachable_end`)

### Requirement: honest infeasibility reporting

The system SHALL distinguish proven infeasibility from search-budget exhaustion and
report them with different warnings; budget exhaustion SHALL NOT be reported as proof
that no valid path exists.

#### Scenario: provably infeasible vs. merely hard
- **GIVEN** one case provably infeasible (insufficient hops to a forced `end_path`) and
  another that is merely hard for an approximate search
- **WHEN** each is run
- **THEN** the two produce distinguishable, explicit outcomes
  (`tests/test_sequence_optimizer.py::test_hard_arc_distinguishes_budget_exhaustion_from_proven_infeasibility`)

### Requirement: mandatory controls survive or fail closed

Locked paths, the manual-order prefix seam, `start_path`, and `end_path` SHALL appear in
the selected subset whenever a valid selection exists; otherwise the call SHALL fail
closed with an explicit warning. A locked or manually-ordered track SHALL never be
silently dropped.

#### Scenario: locked paths and manual seam survive
- **WHEN** locked paths and a manual-order prefix are present
- **THEN** they appear in the result and the seam acts as an external root, never
  selected twice
  (`tests/test_sequence_optimizer.py::test_hard_arc_keeps_locked_paths_and_uses_manual_seam_as_external_root`)

#### Scenario: mandatory paths exceed the target length
- **WHEN** mandatory paths exceed the target length
- **THEN** the call fails closed with an explicit warning
  (`tests/test_sequence_optimizer.py::test_hard_arc_fails_closed_when_mandatory_paths_exceed_target`)

#### Scenario: mandatory paths cannot coexist
- **WHEN** mandatory paths cannot coexist in one BPM-valid path
- **THEN** the call fails closed with an explicit warning and drops nothing silently
  (`tests/test_sequence_optimizer.py::test_hard_arc_fails_closed_when_mandatory_paths_cannot_coexist`)

#### Scenario: mandatory path missing from the pool
- **WHEN** a mandatory path was filtered out upstream or is absent from the pool
- **THEN** the call fails closed with a proven-infeasible warning
  (`tests/test_sequence_optimizer.py::test_hard_arc_reports_a_mandatory_path_missing_from_the_pool`)

#### Scenario: controls survive end to end
- **WHEN** a real `recommend_playlist` call carries a manual prefix, a locked track, and
  an anchor through an arc strategy
- **THEN** the manual track leads, the locked track survives, and the full target count
  is returned
  (`tests/test_playlist_service.py::test_arc_subset_preserves_anchor_locked_track_and_manual_prefix_end_to_end`)

### Requirement: defined edge-case behaviour

The primitive SHALL define and assert behaviour for: `start_path is None`; a candidate
with unknown/missing BPM (treated as pass-through, consistent with existing scoring and
the final gate); `start_path == end_path` with a one-track target; and `arc_length is
None` (fallback to the legacy solvers rather than the subset primitive).

#### Scenario: none-start, missing BPM, and uncapped fallback
- **WHEN** the pool contains a candidate with no BPM, no start is given, and a separate
  call passes `arc_length=None`
- **THEN** the BPM-less candidate is included, the arc still completes, and the uncapped
  call falls back to a legacy optimizer name
  (`tests/test_sequence_optimizer.py::test_hard_arc_defines_none_start_missing_bpm_and_uncapped_fallback`)

#### Scenario: one track can be both start and end
- **WHEN** `start_path == end_path` with a one-track target
- **THEN** the result is exactly that track
  (`tests/test_sequence_optimizer.py::test_hard_arc_one_track_can_be_both_start_and_end`)

### Requirement: folded 2:1 edge comparison in neighbor discovery

The primitive's neighbor discovery SHALL consider BPM windows near `b`, `b/2`, and `2b`
validated through the existing `bpm_difference_percent`, so legal half/double-time pairs
are not silently excluded. Stored BPM values SHALL NOT be reinterpreted, parsed, or
corrected.

#### Scenario: folded pair reachable only through the fold
- **WHEN** the pool contains a legal 60↔120-style pair reachable only through the fold
- **THEN** neighbor discovery admits the edge and the path uses it
  (`tests/test_sequence_optimizer.py::test_hard_arc_neighbor_discovery_includes_folded_two_to_one_edges`)

### Requirement: deterministic hybrid solver

The system SHALL use an exact target-length DP for small feasible domains and a
deterministic beam search otherwise; both paths SHALL be exercised, satisfy the
BPM-ceiling property, and produce identical output on repeat runs.

#### Scenario: exact and beam paths are deterministic and observable
- **WHEN** a small pool forces the exact DP and a large pool forces the beam
- **THEN** the optimizers report `arc-subset-exact` / `arc-subset-beam` respectively and
  repeat beam runs return the identical path
  (`tests/test_sequence_optimizer.py::test_hard_arc_exact_and_beam_paths_are_deterministic_and_observable`)

### Requirement: lazy scoring without eager matrices

The system SHALL compute transition scores per explored edge and arc adherence per
candidate-slot pair on demand, materializing no `pool × pool` or `pool × slot` matrix
for the arc-subset path, and SHALL bound exploration cost on large pools.

#### Scenario: large pool never builds eager matrices
- **WHEN** a multi-thousand-track pool is sequenced through the arc-subset path
- **THEN** `_score_matrix` and `_arc_bonuses` are never invoked
  (`tests/test_sequence_optimizer.py::test_hard_arc_large_pool_never_builds_eager_score_or_arc_matrices`)

#### Scenario: exploration cost is bounded
- **WHEN** a 2,000-track pool is sequenced
- **THEN** `score_transition` calls stay under the exploration budget
  (`tests/test_sequence_optimizer.py::test_hard_arc_beam_bounds_expensive_transition_scoring`)
  and the caller's cache retains only the final path's edges
  (`tests/test_sequence_optimizer.py::test_hard_arc_exploration_only_caches_the_final_path_edges`)

#### Scenario: small-domain arc normalization stays meaningful
- **WHEN** a capped small domain requires a low-scoring connector
- **THEN** the domain-aware arc-bonus normalization does not hide that connector
  (`tests/test_sequence_optimizer.py::test_small_arc_domain_does_not_hide_a_low_arc_bonus_connector`)

## PRESERVED Requirements (no regression)

### Requirement: legacy solvers unchanged for non-arc call shapes

Every call shape that does not set both `arc_strategy` and `max_bpm_difference_percent`
SHALL keep the existing `_exact_path` / `_heuristic_path` behaviour unchanged, and
non-arc strategies SHALL NOT route through the subset search.

#### Scenario: legacy call shapes keep the legacy solvers
- **WHEN** `recommend_sequence` is called without both arc parameters
- **THEN** the legacy solver path is used unchanged
  (`tests/test_sequence_optimizer.py::test_non_hard_arc_call_shapes_keep_the_legacy_solvers`)

#### Scenario: non-arc strategies bypass subset search
- **WHEN** a non-arc strategy (e.g. `chill`) builds a playlist
- **THEN** it keeps its strategy order and never enters the subset search
  (`tests/test_playlist_service.py::test_non_arc_strategy_does_not_route_through_subset_search`,
  `tests/test_playlist_service.py::test_chill_keeps_its_sort`)
