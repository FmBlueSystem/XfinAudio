# AppState Spectral Transition Spec

## Requirement: Apply spectral profiles immutably

### Scenario: Existing track is updated without mutating old state
GIVEN an `AppState` with a scanned track and matching `records_by_path` entry
WHEN a spectral profile is applied for that path
THEN a new `AppState` is returned
AND the new scanned record and dict record contain the spectral profile
AND the original state remains unchanged.

### Scenario: List and dict records stay synchronized
GIVEN an `AppState` with a scanned track and matching `records_by_path` entry
WHEN a spectral profile is applied for that path
THEN both state views contain equivalent updated records for the same path.

### Scenario: Unknown path does not change track contents
GIVEN an `AppState` with scanned records
WHEN a spectral profile is applied for an unknown path
THEN a new `AppState` is returned
AND track contents remain unchanged.
