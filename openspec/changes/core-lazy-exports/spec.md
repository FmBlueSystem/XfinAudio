# Specification: core-lazy-exports

## Requirement: Library pure model imports stay isolated

### Scenario: Importing library models does not load scan or repository infrastructure
Given a fresh Python process
When `xfinaudio.library.models` is imported
Then `xfinaudio.library.scan_service` is not loaded
And `xfinaudio.library.track_repository` is not loaded.

## Requirement: Audio planning imports stay isolated

### Scenario: Importing audio planning does not load analyzers or spectral profile
Given a fresh Python process
When `xfinaudio.audio.analysis_planning` is imported
Then `xfinaudio.audio.batch_analyzer` is not loaded
And `xfinaudio.audio.spectral_profile` is not loaded.

## Requirement: Public package exports remain compatible

### Scenario: Existing library and audio package imports resolve on demand
Given existing callers import public symbols from `xfinaudio.library` and `xfinaudio.audio`
When those symbols are accessed
Then the imports resolve successfully without caller changes.
