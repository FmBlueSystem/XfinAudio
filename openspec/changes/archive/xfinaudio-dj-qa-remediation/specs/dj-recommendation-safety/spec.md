# Delta for DJ Recommendation Safety

## ADDED Requirements

### Requirement: Same-Energy Strategy Enforcement

The system MUST enforce the configured `same_energy` energy tolerance for generated recommendation candidates after the anchor is known.

#### Scenario: Generated candidates outside anchor tolerance are excluded

- GIVEN a selected anchor track with energy `5`
- AND the active strategy is `same_energy`
- AND the strategy energy tolerance is `1`
- WHEN recommendations are generated
- THEN generated candidates with energy `4`, `5`, or `6` MAY be included
- AND generated candidates with energy below `4` or above `6` MUST be excluded.

#### Scenario: DJ-controlled tracks preserve operator authority

- GIVEN a DJ explicitly controls a track through start path, manual prefix, or lock controls
- AND that track is not excluded
- WHEN `same_energy` filtering is applied
- THEN the controlled track MUST remain available to preserve explicit DJ intent
- AND generated candidates MUST still obey the strategy tolerance.

#### Scenario: Missing anchor energy does not create fake precision

- GIVEN the selected anchor has missing or invalid energy metadata
- WHEN `same_energy` recommendations are generated
- THEN the system MUST NOT apply an invented energy tolerance
- AND it MUST surface a warning explaining that energy filtering could not be applied.

### Requirement: Mix-Feasible Candidate Pool Ranking

The system MUST rank recommendation pool candidates by mix feasibility before generic tag overlap.

#### Scenario: BPM-feasible candidate outranks generic tag overlap

- GIVEN an anchor at `102` BPM
- AND candidate A is near `103` BPM with fewer shared generic tags
- AND candidate B is near `126` BPM with more shared generic tags
- WHEN the recommendation candidate pool is ranked
- THEN candidate A MUST rank before candidate B.

#### Scenario: Ranking remains deterministic

- GIVEN two candidates have equivalent BPM feasibility, key compatibility, tag overlap, energy distance, and BPM distance
- WHEN the pool is ranked
- THEN the system MUST use stable deterministic tie-breakers such as path order.

#### Scenario: Harmonic information improves ranking only when available

- GIVEN both anchor and candidate have valid Camelot keys
- WHEN the pool is ranked
- THEN compatible keys SHOULD rank ahead of incompatible keys inside the same BPM feasibility bucket.

### Requirement: Recommendation Safety Warnings

The system MUST keep recommendation safety warnings visible and actionable instead of hiding weak results.

#### Scenario: Dropped candidates explain reduced playlist length

- GIVEN generated tracks are dropped because adjacent BPM jump exceeded the configured limit
- WHEN the recommendation result is displayed
- THEN the warning MUST state how many tracks were dropped and why.

#### Scenario: Strategy filtering explains excluded candidates

- GIVEN `same_energy` filtering excludes generated candidates
- WHEN the recommendation result is displayed
- THEN the warning MUST state that candidates were filtered outside energy tolerance.
