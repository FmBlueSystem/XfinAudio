# Spec Delta: optional-ai-assistance — persisted automatic authorization

## ADDED Requirements
### Requirement: Persisted automatic authorization replaces per-query confirmation when explicitly enabled
The system SHALL persist an `autoAuthorize` boolean (default `false`) inside the
existing AI settings document, exposed by `ai.status` as `autoAuthorize` and
accepted by `ai.settings.update` only as a boolean.

- WHEN `autoAuthorize` is `false`, the host SHALL require the native per-request
  confirmation dialog before `ai.run` (current behavior unchanged).
- WHEN `autoAuthorize` is `true`, the host SHALL NOT fetch `ai.confirmation` and
  SHALL NOT open a dialog: an owned preview id SHALL proceed directly to
  `ai.run` with `confirmed: true`.
- The persisted setting SHALL survive restarts and be revocable from the AI
  settings panel.
- The AI enable switch, credential selection, disclosure text and payload
  review SHALL remain unchanged and required.
