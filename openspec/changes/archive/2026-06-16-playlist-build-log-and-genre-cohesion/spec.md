# Spec: Playlist Build Log + Genre Cohesion

## Capability: recommendation/genre-cohesion

### Requirement: Genre tokens are comma-split for similarity
The transition tag/genre similarity MUST treat a comma-separated genre field as multiple tokens.

#### Scenario: Same-family multi-genre tracks share tokens
- WHEN two tracks have genre `"House, Disco"` and `"House, Funk"`
- THEN their computed genre/tag overlap is greater than 0 (they share the `house` token).

#### Scenario: Unrelated genres share nothing
- WHEN two tracks have genre `"Techno"` and `"Reggae"` and no shared tags
- THEN their computed genre/tag overlap is 0.

### Requirement: Configurable genre cohesion biases sequencing
A `genre_cohesion` value in [0, 1] MUST add a soft penalty to cross-genre transitions, defaulting
to 0.0 (current behavior).

#### Scenario: Cohesion disabled keeps current behavior
- WHEN `genre_cohesion` is 0.0
- THEN the genre cohesion penalty for any transition is exactly 0.0.

#### Scenario: Cohesion penalizes cross-genre adjacency
- WHEN `genre_cohesion` > 0 AND two adjacent tracks share no genre token (both have a genre)
- THEN the transition total receives a positive penalty proportional to `genre_cohesion`.

#### Scenario: Same-genre adjacency is never penalized
- WHEN two adjacent tracks share at least one genre token
- THEN the genre cohesion penalty is 0.0 regardless of `genre_cohesion`.

## Capability: recommendation/build-log

### Requirement: Every recommendation produces a structured build log
`recommend_playlist` MUST produce a `PlaylistBuildLog` describing the construction.

#### Scenario: Stage drop counts reconcile
- WHEN a playlist is recommended from a candidate pool
- THEN the build log lists each construction stage with input/output/dropped counts
- AND the final stage output count equals the number of tracks in the recommendation.

#### Scenario: Per-transition genre relation is recorded
- WHEN a playlist with ≥2 tracks is recommended
- THEN the build log records, for each adjacency, a genre relation of `same`, `overlap`, or `cross`
- AND a `cross_genre_count` equal to the number of `cross` adjacencies.

### Requirement: Build log is persisted with the playlist export
#### Scenario: Exported playlist JSON includes the build log
- WHEN a recommendation is exported as JSON
- THEN the JSON contains a `build_log` block alongside the existing `explanation` block.
