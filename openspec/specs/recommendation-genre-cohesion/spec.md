# Spec: Recommendation Genre Cohesion

## Capability

`recommendation/genre-cohesion`

## Intent

Improve playlist sequencing by treating comma-separated genre fields as multiple similarity tokens and by allowing DJs to opt into a soft bias against cross-genre transitions.

## Requirements

### Requirement: Genre tokens are comma-split for similarity
The transition tag/genre similarity MUST treat a comma-separated genre field as multiple tokens.

#### Scenario: Same-family multi-genre tracks share tokens
- WHEN two tracks have genre `"House, Disco"` and `"House, Funk"`
- THEN their computed genre/tag overlap is greater than 0 (they share the `house` token).

#### Scenario: Unrelated genres share nothing
- WHEN two tracks have genre `"Techno"` and `"Reggae"` and no shared tags
- THEN their computed genre/tag overlap is 0.

### Requirement: Configurable genre cohesion biases sequencing
A `genre_cohesion` value in [0, 1] MUST add a soft penalty to cross-genre transitions, defaulting to 0.0 (current behavior).

#### Scenario: Cohesion disabled keeps current behavior
- WHEN `genre_cohesion` is 0.0
- THEN the genre cohesion penalty for any transition is exactly 0.0.

#### Scenario: Cohesion penalizes cross-genre adjacency
- WHEN `genre_cohesion` > 0 AND two adjacent tracks share no genre token (both have a genre)
- THEN the transition total receives a positive penalty proportional to `genre_cohesion`.

#### Scenario: Same-genre adjacency is never penalized
- WHEN two adjacent tracks share at least one genre token
- THEN the genre cohesion penalty is 0.0 regardless of `genre_cohesion`.
