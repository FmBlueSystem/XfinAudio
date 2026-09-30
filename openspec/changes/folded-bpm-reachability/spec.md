# Requirements

## R1: Folded component correctness
GIVEN an unordered pool with measurable BPMs and an anchor
WHEN the pool is filtered for BPM reachability
THEN it keeps every generated track connected by a chain of edges accepted by
the existing folded BPM comparator at the requested ceiling, including
half/double-time edges separated in sorted order by unrelated tracks.

GIVEN 60, 90, and 120 BPM complete tracks with a 60 BPM start
WHEN harmonic_journey requests two tracks
THEN it returns the playable 60 and 120 BPM tracks and drops only 90 BPM.

## R2: Stable passthrough and selection
GIVEN protected control tracks and unknown-BPM tracks
WHEN reachability is computed
THEN they survive, without becoming new bridges (except the measurable anchor).
GIVEN no measurable anchor
WHEN multiple components exist
THEN the largest component is selected, ties resolved by its lowest BPM/path.
The kept list preserves original input order and reports the exact dropped count.

## R3: Bounded discovery
GIVEN a dense large pool
WHEN reachability is computed
THEN it does not construct or compare every pair of candidates.
