# Delta for Same Color & Energy Strategy

## ADDED Requirements

### Requirement: Camelot Is Independent of Spectral Eligibility

`same_color_energy` MUST preserve Camelot scoring and gates; it MUST NOT require exact anchor key or use key as spectral eligibility.

#### Scenario: Compatible different key remains eligible

- GIVEN a candidate meets strict eligibility
- WHEN its key is compatible but differs from the anchor
- THEN it MUST remain eligible for ranking under harmonic rules

## MODIFIED Requirements

### Requirement: Hard Anchor-Color Prefilter Applies

Anchor identity MUST resolve to a single track path, in order: the start-path track; else the first manual-prefix record carrying the majority manual color; else the first profiled record. (Selecting the majority manual COLOR is insufficient — the anchor is a specific path, so the tiebreak MUST name the first manual-prefix record carrying that color.) Every generated candidate MUST share the resolved anchor's dominant-color label and exact energy.

For RED/GREEN/BLUE anchors, dominant-color label equality is sufficient (plus exact energy). For a MIXED anchor, label equality is necessary but NOT sufficient: candidates MUST additionally pass a bounded anchor-relative proximity gate over cached RGB ratios (L1 distance), spectral centroid (relative difference), and rolloff (relative difference), each compared against a named constant. The numeric bounds are calibration-provisional named constants — `MIXED_RGB_L1_MAX` (initial `0.08`), `MIXED_CENTROID_REL_MAX` (initial `0.15`), `MIXED_ROLLOFF_REL_MAX` (initial `0.15`) — and the literal values MUST NOT be treated as frozen; only the RULE SHAPE (label equality plus the bounded RGB L1 / centroid / rolloff gate expressed through named constants) is normative. The bounded gate itself is required because MIXED is the ELSE of three independent threshold tests and spans an L1 diameter of 0.30 while holding a large residual share of the library, so label equality alone constrains nothing.

(Previously: Matching the resolved dominant-color label was sufficient for every candidate. Anchor precedence identified a color rather than a specific path, and the numeric bounds were stated as frozen normative values.)

#### Scenario: MIXED candidates meet proximity bounds

- GIVEN a MIXED anchor with cached profile values
- WHEN `same_color_energy` generates recommendations
- THEN every generated MIXED candidate MUST satisfy the label AND the bounded anchor-relative RGB L1 / centroid / rolloff proximity gate expressed through the calibration-provisional named constants

#### Scenario: Missing anchor prerequisite fails closed

- GIVEN an anchor lacks energy, color, or MIXED profile data
- WHEN `same_color_energy` generates recommendations
- THEN generated candidates MUST be empty and a prerequisite warning MUST be emitted

#### Scenario: Locked controls do not determine anchor

- GIVEN a locked control conflicts with manual-prefix majority and no start-path exists
- WHEN the anchor is resolved for `same_color_energy`
- THEN the anchor MUST be the first manual-prefix record carrying the majority manual color, and locked controls MUST NOT select the anchor

### Requirement: Hard Energy Band Composes With the Color Filter

For `same_color_energy`, generated candidates MUST exactly equal the resolved anchor `energy_level`. Combined color-and-energy eligibility MUST be applied before pool capping.

(Previously: Candidates could be within an anchor-relative ±1 energy band.)

#### Scenario: Candidates satisfy exact combined eligibility

- GIVEN an anchor with resolved color and energy
- WHEN `same_color_energy` generates recommendations
- THEN every generated candidate MUST satisfy strict color and exact anchor energy before capping

### Requirement: Control Paths Are Preserved

Controls MUST pass through combined filtering without exclusion or re-scoring. They MAY remain even when they fail strict generated-candidate eligibility.

(Previously: Control tracks were preserved through the original combined filters.)

#### Scenario: Controls remain in their positions

- GIVEN locked, start, end, and manual-prefix tracks
- WHEN `same_color_energy` generates recommendations
- THEN all controls MUST remain in their existing positions

### Requirement: Strict Empty-Pool and Shortage Warnings

With no strict generated candidate, the system MUST NOT fall back to unfiltered scoring and MUST warn why. With fewer eligible candidates than requested slots, it MUST return only them and warn. `same_color` and `same_energy` fallback behavior and warning text MUST remain unchanged.

(Previously: An empty combined pool fell back to unfiltered scoring.)

#### Scenario: Empty strict pool does not widen

- GIVEN strict eligibility excludes every non-control candidate
- WHEN `same_color_energy` generates recommendations
- THEN only preserved controls or no generated candidates MUST be returned
- AND a strict-constraint warning MUST be emitted

#### Scenario: Strict pool is shorter than requested

- GIVEN eligible generated candidates are fewer than requested generated slots
- WHEN `same_color_energy` generates recommendations
- THEN every returned generated candidate MUST remain eligible
- AND a shortage warning MUST be emitted

#### Scenario: Existing strategy warnings are unaffected

- GIVEN `same_color` or `same_energy` triggers its own fallback
- WHEN its warning is emitted
- THEN its wording MUST remain unchanged

### Requirement: Guarantee-Explicit Descriptions

`same_color_energy` description MUST state hard anchor-color filtering and exact anchor energy. `same_color` and `same_energy` descriptions MUST remain unchanged.

(Previously: same_color_energy described a hard ±1 energy band.)

#### Scenario: Combined description states strict guarantees

- GIVEN the registered `same_color_energy` profile
- WHEN its description is read
- THEN it MUST state hard anchor-color filtering and exact anchor energy

#### Scenario: Existing descriptions retain guarantees

- GIVEN the registered `same_color` and `same_energy` profiles
- WHEN their descriptions are read
- THEN their existing guarantee descriptions MUST remain unchanged
