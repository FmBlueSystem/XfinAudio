# Same Color Strategy Specification

## Purpose

Define the observable behavior of the `same_color` playlist recommendation
strategy. `same_color` constrains the set to the anchor's spectral colour and
nothing else: energy stays a weighted scoring preference and is never a filter.

The colour constraint is a HARD filter, and label equality alone does not deliver
one — `_dominant_color()` classifies by crossing per-band thresholds that are
unbounded above, so a shared label admits dispersion up to L1 `0.71` on the real
library while the strategy's registered description promises a "Hard filter".
`same_color` therefore applies the same bounded anchor-relative proximity gate
its sibling `same_color_energy` applies, minus the exact-energy predicate, and
fails closed rather than widening to the unfiltered library.

This capability governs `same_color` only. `same_color_energy` is governed by the
`same-color-energy-strategy` capability; the two share one gate implementation
and differ by a single predicate.

## Requirements

### Requirement: Bounded Anchor-Color Gate Applies to Every Candidate

`same_color` MUST admit a generated candidate only when it satisfies dominant-color label equality with the resolved anchor AND passes the bounded anchor-relative proximity gate over cached RGB ratios (L1 distance), spectral centroid (relative difference), and rolloff (relative difference), each compared against a colour-neutral named constant. This gate MUST apply for EVERY anchor colour (RED, GREEN, BLUE, MIXED); label equality alone is necessary but NOT sufficient. The gate constants MUST be the same colour-neutral named constants used by `same_color_energy` (for example `COLOR_RGB_L1_MAX`, `COLOR_CENTROID_REL_MAX`, `COLOR_ROLLOFF_REL_MAX`, values `0.08`, `0.15`, `0.15`); the literal values are NOT normative — only the RULE SHAPE is. `same_color`'s registered description claims a "Hard filter", and plain label equality admits dispersion up to L1 `0.71` on the real library, so the bounded gate is required to make the description true.

#### Scenario: Every colour candidate meets label AND proximity bounds

- GIVEN an anchor with a resolved dominant-color label (RED, GREEN, BLUE, or MIXED) and cached profile values
- WHEN `same_color` generates recommendations
- THEN every generated candidate MUST satisfy label equality AND the bounded anchor-relative RGB L1 / centroid / rolloff proximity gate

#### Scenario: Same-label candidate outside the gate is rejected

- GIVEN an anchor and a candidate sharing the anchor's label whose anchor-relative RGB L1 exceeds `COLOR_RGB_L1_MAX`
- WHEN `same_color` generates recommendations
- THEN that candidate MUST NOT appear as a generated candidate

#### Scenario: Candidate exactly at a bound is eligible

- GIVEN an anchor and a candidate sharing label whose anchor-relative RGB L1 equals `COLOR_RGB_L1_MAX`, centroid relative delta equals `COLOR_CENTROID_REL_MAX`, and rolloff relative delta equals `COLOR_ROLLOFF_REL_MAX`
- WHEN `same_color` generates recommendations
- THEN that candidate MUST be eligible (bounds are inclusive)

#### Scenario: Invalid profile or degenerate denominator fails closed

- GIVEN an anchor or candidate with missing/non-finite RGB ratios, a non-positive RGB sum, or a zero/non-finite centroid or rolloff denominator on the anchor
- WHEN `same_color` generates recommendations
- THEN the affected candidate MUST be rejected rather than admitted on a degenerate comparison

### Requirement: Energy Remains Weighted, Never Limited

`same_color` MUST NOT acquire an energy filter. Energy MUST remain a weighted scoring preference; only the colour constraint is a hard filter.

#### Scenario: Candidates outside the anchor energy still eligible

- GIVEN a candidate that passes the bounded colour gate but whose energy level differs from the anchor
- WHEN `same_color` generates recommendations
- THEN that candidate MUST remain eligible, with energy affecting only its weighted score, not its eligibility

### Requirement: Control Paths Remain User-Owned Exceptions

Locked, start, end, and manual control tracks MUST pass through the bounded colour gate without exclusion or re-scoring. They MAY remain even when they fail the strict generated-candidate gate.

#### Scenario: Controls remain in their positions

- GIVEN locked, start, end, and manual-prefix tracks, some failing the bounded colour gate
- WHEN `same_color` generates recommendations
- THEN all controls MUST remain present in their existing positions, unaffected by the gate

### Requirement: Empty Strict Pool Fails Closed

When the bounded colour gate leaves no generated candidate, `same_color` MUST NOT fall back to unfiltered scoring. It MUST return only preserved controls (or no generated candidates) and MUST emit an explicit warning attributing the empty result to the strict colour constraint. A strategy whose registered description claims a "Hard filter" MUST NOT silently widen to the entire library; failing closed also keeps `same_color` consistent with its sibling `same_color_energy`, which already fails closed.

#### Scenario: Empty strict pool does not widen

- GIVEN the bounded colour gate excludes every non-control candidate
- WHEN `same_color` generates recommendations
- THEN only preserved controls or no generated candidates MUST be returned
- AND an explicit strict-colour-constraint warning MUST be emitted
- AND the unfiltered library MUST NOT be returned

#### Scenario: Missing anchor prerequisite fails closed

- GIVEN no anchor can be resolved, or the resolved anchor carries no spectral profile
- WHEN `same_color` generates recommendations
- THEN generated candidates MUST be empty and a prerequisite warning MUST be emitted, and the unfiltered library MUST NOT be returned
