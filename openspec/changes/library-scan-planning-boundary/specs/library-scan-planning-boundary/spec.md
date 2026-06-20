# Spec: Library scan planning boundary

## Requirement: Scan candidate planning is pure

XfinAudio SHALL expose a pure library scan planning function that returns deterministic supported audio candidates without reading tags, analyzing audio, touching UI, or persisting data.

### Scenario: Planner deduplicates supported paths

Given a path lister returns repeated supported audio paths,
When scan candidates are planned,
Then each supported audio path SHALL appear once in deterministic order.

## Requirement: Scan execution uses planned candidates

`scan_folder()` SHALL use the pure planner before reading metadata or resolving spectral profiles.

### Scenario: Duplicate lister entries are read once

Given a scan path lister returns the same supported audio path more than once,
When `scan_folder()` reads metadata,
Then the tag reader SHALL be called once for that path and the scan result SHALL contain one track record.
