# Same Color & Energy Strategy Specification

## Purpose

Define the observable behavior of the `same_color_energy` playlist
recommendation strategy, which composes a hard anchor-color constraint with a
hard exact-energy constraint as combined, non-negotiable eligibility. The color
constraint is not label equality alone: for EVERY dominant-color label the
strategy also requires a bounded anchor-relative proximity gate over cached
spectral values. The strategy fails closed — it never widens to unfiltered
scoring.

This capability governs `same_color_energy` only. The sibling `same_color`
strategy shares the same bounded colour gate and is governed by the
`same-color-strategy` capability; `same_energy` and every other registered
strategy are unaffected by this capability and are protected by the
Untouched Sibling Strategies requirement below.

## Requirements

### Requirement: Strategy Registration and Enumeration

The system MUST register a `same_color_energy` strategy profile (label
"Same Color & Energy") in `_STRATEGIES`, extend the `StrategyName` Literal
to include it, and make it discoverable through the same enumeration
surfaces used by every other strategy.

#### Scenario: Strategy is selectable via the catalog

- GIVEN the strategy catalog is queried through `list_strategy_catalog()` or
  `available_strategies()`
- WHEN the catalog is enumerated
- THEN `same_color_energy` MUST appear with its display label
- AND selecting it MUST resolve to a valid `_STRATEGIES` entry with no
  bespoke UI wiring required

#### Scenario: Strategy name is statically typed

- GIVEN the `StrategyName` Literal type
- WHEN `pyright` checks `src` and `tests`
- THEN `"same_color_energy"` MUST be a valid `StrategyName` member with no
  new type errors

### Requirement: Camelot Is Independent of Spectral Eligibility

`same_color_energy` MUST preserve Camelot scoring and gates; it MUST NOT require exact anchor key or use key as spectral eligibility.

#### Scenario: Compatible different key remains eligible

- GIVEN a candidate meets strict eligibility
- WHEN its key is compatible but differs from the anchor
- THEN it MUST remain eligible for ranking under harmonic rules

### Requirement: Hard Anchor-Color Prefilter Applies

Anchor identity MUST resolve to a single track path, in order: the start-path track; else the first manual-prefix record carrying the majority manual color; else the first profiled record. Every generated candidate MUST share the resolved anchor's dominant-color label and exact energy.

The bounded anchor-relative proximity gate MUST apply to EVERY generated candidate regardless of the anchor's dominant-color label. For RED, GREEN, BLUE and MIXED anchors alike, dominant-color label equality is necessary but NOT sufficient: a candidate MUST additionally pass a bounded anchor-relative proximity gate over cached RGB ratios (L1 distance), spectral centroid (relative difference), and rolloff (relative difference), each compared against a named constant. The gate constants MUST carry colour-neutral names (for example `COLOR_RGB_L1_MAX`, `COLOR_CENTROID_REL_MAX`, `COLOR_ROLLOFF_REL_MAX`); the `MIXED_` prefix is forbidden because the gate no longer applies to MIXED only. The numeric bounds are named constants (values `0.08`, `0.15`, `0.15` respectively) and the literal values MUST NOT be treated as frozen; only the RULE SHAPE — label equality plus the bounded RGB L1 / centroid / rolloff gate expressed through colour-neutral named constants, applied to every colour — is normative. The gate applies to RED/GREEN/BLUE because `_dominant_color()` classifies by crossing per-band thresholds that are unbounded above: RED/GREEN/BLUE anchors are MORE dispersed than MIXED (measured max pairwise L1 up to `0.71` vs MIXED `0.28`), so label equality alone constrains RED/GREEN/BLUE no more than it constrained MIXED.

#### Scenario: Every colour candidate meets proximity bounds

- GIVEN an anchor with a resolved dominant-color label (RED, GREEN, BLUE, or MIXED) and cached profile values
- WHEN `same_color_energy` generates recommendations
- THEN every generated candidate MUST satisfy label equality AND the bounded anchor-relative RGB L1 / centroid / rolloff proximity gate

#### Scenario: RED/GREEN/BLUE candidate outside the gate is rejected

- GIVEN a RED, GREEN, or BLUE anchor and a candidate sharing that label whose anchor-relative RGB L1 exceeds `COLOR_RGB_L1_MAX`
- WHEN `same_color_energy` generates recommendations
- THEN that candidate MUST NOT appear as a generated candidate

#### Scenario: Gate is expressed through colour-neutral named constants

- GIVEN the eligibility gate implementation
- WHEN its RGB L1, centroid, and rolloff bounds are inspected
- THEN each bound MUST be a colour-neutral named constant applied identically to every colour, and no `MIXED_`-prefixed gate constant MUST remain

#### Scenario: Candidate exactly at a bound is eligible

- GIVEN an anchor and a candidate sharing label and exact energy whose anchor-relative RGB L1 equals `COLOR_RGB_L1_MAX`, centroid relative delta equals `COLOR_CENTROID_REL_MAX`, and rolloff relative delta equals `COLOR_ROLLOFF_REL_MAX`
- WHEN `same_color_energy` generates recommendations
- THEN that candidate MUST be eligible (bounds are inclusive)

#### Scenario: Missing or invalid profile data fails closed

- GIVEN an anchor or candidate whose RGB ratios are missing or non-finite, or whose RGB sum is not positive
- WHEN `same_color_energy` generates recommendations
- THEN that candidate MUST be rejected and MUST NOT be admitted on a degenerate comparison

#### Scenario: Zero or non-finite relative-delta denominator fails closed

- GIVEN an anchor whose centroid or rolloff is zero, negative, or non-finite (the relative-delta denominator)
- WHEN `same_color_energy` evaluates a candidate against that anchor
- THEN the candidate MUST be rejected rather than admitted

#### Scenario: Missing anchor prerequisite fails closed

- GIVEN an anchor lacks energy, color, or profile data
- WHEN `same_color_energy` generates recommendations
- THEN generated candidates MUST be empty and a prerequisite warning MUST be emitted

#### Scenario: Locked controls do not determine anchor

- GIVEN a locked control conflicts with manual-prefix majority and no start-path exists
- WHEN the anchor is resolved for `same_color_energy`
- THEN the anchor MUST be the first manual-prefix record carrying the majority manual color, and locked controls MUST NOT select the anchor

### Requirement: Hard Energy Band Composes With the Color Filter

For `same_color_energy`, generated candidates MUST exactly equal the resolved anchor `energy_level`. Combined color-and-energy eligibility MUST be applied before pool capping.

#### Scenario: Candidates satisfy exact combined eligibility

- GIVEN an anchor with resolved color and energy
- WHEN `same_color_energy` generates recommendations
- THEN every generated candidate MUST satisfy strict color and exact anchor energy before capping

### Requirement: Control Paths Are Preserved

Controls MUST pass through combined filtering without exclusion or re-scoring. They MAY remain even when they fail strict generated-candidate eligibility.

#### Scenario: Controls remain in their positions

- GIVEN locked, start, end, and manual-prefix tracks
- WHEN `same_color_energy` generates recommendations
- THEN all controls MUST remain in their existing positions

### Requirement: Empty-Pool Fallback With Strategy-Aware Warning

With no strict generated candidate, `same_color_energy` MUST NOT fall back to unfiltered scoring and MUST warn why. With fewer eligible candidates than requested slots, it MUST return only them and warn. `same_energy` fallback behavior and warning text MUST remain unchanged, and `same_color`'s is governed by the `same-color-strategy` capability.

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

### Requirement: Untouched Sibling Strategies

Applying the bounded proximity gate to all colours MUST NOT change the observable behaviour of `same_energy`, `same_genre`, `harmonic_journey`, `warmup`, `build`, `peak_time`, `chill`, or `same_vibe`. `same_energy` MUST retain its `±1` anchor-relative energy band and its registered description verbatim. Camelot scoring and gates MUST remain independent of spectral eligibility. `_dominant_color()` classification and its per-band thresholds MUST NOT change.

#### Scenario: same_energy band and description are unchanged

- GIVEN the registered `same_energy` profile and a fixed pool and anchor
- WHEN recommendations are generated
- THEN `same_energy` MUST hold candidates to its `±1` anchor-relative energy band through the shared energy-tolerance mechanism, and its ordered candidate list, warnings, and registered description MUST be exactly what they were before the bounded colour gate existed

#### Scenario: Unrelated strategies are unaffected

- GIVEN `same_genre`, `harmonic_journey`, `warmup`, `build`, `peak_time`, `chill`, or `same_vibe` with a fixed pool and anchor
- WHEN recommendations are generated
- THEN the ordered candidate list and any warnings MUST be exactly what they were before the bounded colour gate existed, including `same_genre`'s own unfiltered-pool fallback and its warning text

#### Scenario: Camelot and dominant-color classification are independent

- GIVEN a candidate whose Camelot key is compatible but different from the anchor
- WHEN `same_color_energy` evaluates eligibility
- THEN Camelot compatibility MUST NOT affect spectral eligibility, and `_dominant_color()` MUST classify the candidate by its unchanged per-band thresholds

### Requirement: Guarantee-Explicit Descriptions

`same_color_energy` description MUST state hard anchor-color filtering and exact anchor energy. `same_color` and `same_energy` descriptions MUST remain unchanged.

#### Scenario: Combined description states strict guarantees

- GIVEN the registered `same_color_energy` profile
- WHEN its description is read
- THEN it MUST state hard anchor-color filtering and exact anchor energy

#### Scenario: Existing descriptions retain guarantees

- GIVEN the registered `same_color` and `same_energy` profiles
- WHEN their descriptions are read
- THEN their existing guarantee descriptions MUST remain unchanged
