# AppState Transitions Capability

## ADDED Requirements

### Requirement: Spectral profile application is immutable
XfinAudio SHALL apply background spectral profile updates through a pure AppState transition that returns a new state and does not mutate existing state collections.

#### Scenario: Existing track is updated without mutating old state
- GIVEN an `AppState` with a scanned track and matching `records_by_path` entry
- WHEN a spectral profile is applied for that path
- THEN the returned `AppState` is not the input instance
- AND the returned scanned record has the spectral profile
- AND the returned `records_by_path` record has the spectral profile
- AND the input state still has no spectral profile for that track

#### Scenario: Unknown path leaves track contents unchanged
- GIVEN an `AppState` with scanned records
- WHEN a spectral profile is applied for an unknown path
- THEN the returned `AppState` is not the input instance
- AND the returned collections are copied
- AND the track contents remain unchanged
