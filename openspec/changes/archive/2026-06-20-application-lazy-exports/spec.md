# Specification: application-lazy-exports

## Requirement: Application submodule imports stay isolated

### Scenario: Importing saved playlists does not load playlist workflow or vertical flow
Given a fresh Python process
When `xfinaudio.application.saved_playlists` is imported
Then `xfinaudio.application.playlist_workflow` is not loaded
And `xfinaudio.application.vertical_playlist_flow` is not loaded.

## Requirement: Public application exports remain compatible

### Scenario: Existing application package imports resolve on demand
Given existing callers import public symbols from `xfinaudio.application`
When those symbols are accessed
Then the imports resolve successfully without caller changes.
