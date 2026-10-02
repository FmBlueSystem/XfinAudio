# AI Settings and explicit connection testing

## Intent
Make the existing optional Nan Builders adapter configurable and understandable in desktop Settings, preserving a fully usable offline app.

## Scope and consent
- Expose enabled state, the supported provider, credential-file path selection, safe setup guidance, and current status.
- Explain the data sent for explicit AI actions and for a synthetic connection probe.
- Apply saved changes immediately. Opening, editing, cancelling, and resetting the dialog never issue AI requests.
- Keep keys outside settings and the UI. Existing environment credentials take precedence over file credentials.
- No audio/Serato writes, DSP, new dependencies, live API calls during development, or persistent credential provisioning.

## Chained review plan
This change exceeds 400 changed lines overall. Each conventional commit is a dependent review slice limited to 400 changed lines (additions plus deletions):
1. SDD approval record and runtime/probe contracts.
2. Runtime configuration and synthetic probe, with RED/GREEN evidence.
3. AI settings controls and disclosure, with RED/GREEN evidence.
4. Non-blocking probe, cancellation and retry, with RED/GREEN evidence.
5. Controller integration, regression tests and verification record.
Split a slice further before exceeding its budget. No monolithic delivery.

## Risks and rollback
Persisted settings must not claim success when save fails. Cancellation invalidates probe results; an already sent request cannot be recalled. Revert dependent slices in reverse order. No settings schema migration is needed.

## Success
Offline, missing-key, invalid configuration, authentication, retry and cancellation are covered without network or real credentials. Existing loudness controls and defaults remain unchanged. Coordinator runs the final release gate on the integrated commit.
