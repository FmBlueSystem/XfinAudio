# Spec: Recommendation candidate key safety

## Requirement: Candidate pool handles invalid Camelot keys safely

XfinAudio SHALL keep building the recommendation candidate pool when a track has an invalid Camelot key.

### Scenario: Invalid candidate key does not crash pool building

Given a complete candidate track has an invalid Camelot key,
When the recommendation candidate pool is built from a valid anchor,
Then pool building SHALL return candidate records instead of raising an exception.

### Scenario: Valid compatible keys keep ranking ahead of invalid keys

Given one candidate has a valid compatible Camelot key and another candidate has an invalid Camelot key,
When the recommendation candidate pool is built from an anchor,
Then the valid compatible candidate SHALL rank ahead of the invalid-key candidate when other similarity signals are otherwise comparable.
