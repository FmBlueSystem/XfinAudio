# Spec: Audio analysis planning boundary

## Requirement: Batch analysis planning is pure

XfinAudio SHALL expose pure planning logic that separates cache-hit selection from executor dispatch.

### Scenario: Cached profiles are returned without executor work

Given a path with a fresh cached spectral profile,
When batch analysis is planned,
Then the profile SHALL be returned as an immediate result and the path SHALL not be scheduled for analysis.

## Requirement: Duplicate pending paths are deduplicated

XfinAudio SHALL schedule each uncached path string at most once per batch analysis request.

### Scenario: Duplicate uncached path appears once in pending work

Given the same uncached path appears multiple times in a batch request,
When batch analysis is planned,
Then the pending work SHALL contain that path only once.
