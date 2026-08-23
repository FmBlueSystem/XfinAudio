# Delta Specification: Watcher-Loudness Integration

## Requirement: Bounded loudness tag-write suppression

The library watcher SHALL accept exact paths to suppress for a positive,
bounded interval. Suppression SHALL be checked before debounce and SHALL expire
without retaining a permanent path exclusion.

### Scenario: App tag-write event is ignored
- **GIVEN** loudness completion has registered the path it is about to write
- **WHEN** the watcher receives that path before the interval expires
- **THEN** it does not set `changes_detected_since_scan` or emit a rescan signal

### Scenario: External event still reaches the affordance
- **GIVEN** a suppression exists for one track
- **WHEN** a different library path changes
- **THEN** normal debounce and rescan-affordance behavior remains intact

### Scenario: Expired path returns to normal detection
- **GIVEN** a suppression interval has elapsed
- **WHEN** the formerly suppressed path changes
- **THEN** it is detected as an external filesystem change
