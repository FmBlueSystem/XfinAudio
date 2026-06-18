# Spec: Hidden Bug Hardening

## Requirements

### Requirement: Recommendation constraints remain valid after BPM validation

The recommendation service SHALL optimize candidate order before applying BPM jump validation, and SHALL report any terminal control that cannot survive BPM validation.

#### Scenarios

- Given a start track at 100 BPM, a bridge track at 103 BPM, and another track at 106 BPM, when recommending a harmonic journey, then the system keeps all three in the valid 100 -> 103 -> 106 order.
- Given a selected start path, when BPM validation drops incompatible generated tracks, then the selected start path remains first.
- Given an end path that is dropped by BPM validation, then the returned applied controls report `end_path` as `None` and include an explicit warning.

### Requirement: Desktop UI state does not retain stale track constraints

The desktop UI SHALL clear hidden selections after filtering and SHALL clear selected paths and constraints when the scan folder changes.

#### Scenarios

- Given a selected visible track, when a search filter hides it, then recommendation controls no longer use that hidden track as an anchor.
- Given selected/excluded/locked tracks from folder A, when the user selects folder B, then selection and constraints are cleared.
- Given tracks are shown through `show_tracks`, then `AppState.scanned_records` and `records_by_path` reflect the rendered tracks.

### Requirement: Genre enrichment settings are honored end to end

The app SHALL preserve genre decisions in display-track loads, honor per-provider enable flags, preserve non-UI genre settings, and pass the active enrichment service into desktop scans.

#### Scenarios

- Given a persisted `genre_decision`, when display tracks are loaded, then the decision is present in the returned `TrackRecord`.
- Given a provider disabled in settings, when enrichment runs, then that provider is not called.
- Given custom trust thresholds in settings, when SettingsDialog is accepted, then those fields are preserved.
- Given a workflow has an enrichment service factory, when scanning, then the created service is passed to the scan service.

### Requirement: Provider transient failures are retryable

Runtime providers SHALL NOT cache transient failures as empty successful lookups.

#### Scenarios

- Given Last.fm, Spotify, or Deezer fails once and succeeds on the next call, when a cache path is configured, then the second call retries and returns candidates.
