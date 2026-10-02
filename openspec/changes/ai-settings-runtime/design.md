# Design

## Runtime compatibility
`ai/runtime_settings.py` supplies `effective_ai_settings` and `apply_ai_settings`. Startup retains existing environment-override semantics. The dialog reflects effective configuration. An explicit successful save updates the existing environment bridge; no credential values are changed. The controller changes runtime configuration only after persistence succeeds.

## Probe boundary
`ai/connection_test.py` performs a bounded synthetic request through `nan_client.chat(enabled=...)` with the unsaved candidate configuration. This explicit override does not mutate ambient runtime state. Structured statuses carry safe, fixed messages. Preflight checks key presence/file existence only, not file content. Only a user-triggered probe invokes the adapter to read credentials.

## Desktop
`AiSettingsPanel` owns editable opt-in, supported provider selection, a path label/file chooser, disclosures and status. No key text entry exists. A background thread owns each bounded probe; cancellation is logical and results from obsolete requests are ignored. SettingsDialog embeds the panel and supports `focus_ai`; SettingsController supports `open_ai_settings_dialog`.

## Safety
Never render a provider response or exception detail. The existing redirect rejection stays in place. Disabling AI takes effect on subsequent requests; in-flight requests cannot be recalled. No changes to audio, loudness, library, Serato, dependencies or export boundaries.
