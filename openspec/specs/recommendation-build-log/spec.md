# Spec: Recommendation Build Log

## Capability

`recommendation/build-log`

## Intent

Expose a structured, read-only audit trail for playlist recommendation construction so DJs can understand filtering stages and genre adjacency outcomes.

## Requirements

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
