# Delta for Same Color & Energy Strategy

## MODIFIED Requirements

### Requirement: Hard Anchor-Color Prefilter Applies

Anchor identity MUST resolve to a single track path, in order: the start-path track; else the first manual-prefix record carrying the majority manual color; else the first profiled record. Every generated candidate MUST share the resolved anchor's dominant-color label and exact energy.

The bounded anchor-relative proximity gate MUST apply to EVERY generated candidate regardless of the anchor's dominant-color label. For RED, GREEN, BLUE and MIXED anchors alike, dominant-color label equality is necessary but NOT sufficient: a candidate MUST additionally pass a bounded anchor-relative proximity gate over cached RGB ratios (L1 distance), spectral centroid (relative difference), and rolloff (relative difference), each compared against a named constant. The gate constants MUST carry colour-neutral names (for example `COLOR_RGB_L1_MAX`, `COLOR_CENTROID_REL_MAX`, `COLOR_ROLLOFF_REL_MAX`); the `MIXED_` prefix is forbidden because the gate no longer applies to MIXED only. The numeric bounds are calibration-provisional named constants (initial values `0.08`, `0.15`, `0.15` respectively) and the literal values MUST NOT be treated as frozen; only the RULE SHAPE — label equality plus the bounded RGB L1 / centroid / rolloff gate expressed through colour-neutral named constants, applied to every colour — is normative. The gate applies to RED/GREEN/BLUE because `_dominant_color()` classifies by crossing per-band thresholds that are unbounded above: RED/GREEN/BLUE anchors are MORE dispersed than MIXED (measured max pairwise L1 up to `0.71` vs MIXED `0.28`), so label equality alone constrains RED/GREEN/BLUE no more than it constrained MIXED.

(Previously: For RED/GREEN/BLUE anchors, dominant-color label equality was sufficient and only MIXED anchors required the bounded proximity gate; the gate constants carried the `MIXED_` prefix.)

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

### Requirement: Empty-Pool Fallback With Strategy-Aware Warning

With no strict generated candidate, `same_color_energy` MUST NOT fall back to unfiltered scoring and MUST warn why. With fewer eligible candidates than requested slots, it MUST return only them and warn. `same_color` and `same_energy` fallback behavior and warning text MUST remain unchanged except where a separate delta for `same_color` modifies it.

(Previously: An empty combined pool fell back to the `same_color` fallback-to-unfiltered scoring path.)

#### Scenario: Empty strict pool does not widen

- GIVEN strict eligibility excludes every non-control candidate
- WHEN `same_color_energy` generates recommendations
- THEN only preserved controls or no generated candidates MUST be returned
- AND a strict-constraint warning MUST be emitted

## ADDED Requirements

### Requirement: Untouched Sibling Strategies

Extending the bounded proximity gate to all colours MUST NOT change the observable behaviour of `same_energy`, `same_genre`, `harmonic_journey`, `warmup`, `build`, `peak_time`, `chill`, or `same_vibe`. `same_energy` MUST retain its `±1` anchor-relative energy band and its registered description verbatim. Camelot scoring and gates MUST remain independent of spectral eligibility. `_dominant_color()` classification and its per-band thresholds MUST NOT change.

#### Scenario: same_energy band and description are unchanged

- GIVEN the registered `same_energy` profile and a fixed pool and anchor
- WHEN recommendations are generated before and after this change
- THEN the `±1` energy band, ordered candidate list, warnings, and description MUST be identical

#### Scenario: Unrelated strategies are unaffected

- GIVEN `same_genre`, `harmonic_journey`, `warmup`, `build`, `peak_time`, `chill`, or `same_vibe` with a fixed pool and anchor
- WHEN recommendations are generated before and after this change
- THEN the ordered candidate list and any warnings MUST be identical

#### Scenario: Camelot and dominant-color classification are independent

- GIVEN a candidate whose Camelot key is compatible but different from the anchor
- WHEN `same_color_energy` evaluates eligibility
- THEN Camelot compatibility MUST NOT affect spectral eligibility, and `_dominant_color()` MUST classify the candidate by its unchanged per-band thresholds
