# Optional structured AI interpretation
Translate user-approved Library, Editor and saved-set requests through the configured Nan adapter while retaining local helpers. The model interprets language; local validators, query matching, edit engine and comparison renderer remain authoritative. No audio, filesystem paths, raw tags, persisted playlist IDs or credentials enter model messages.

## Scope and delivery
Use strict TDD and chained commits of at most 400 changed lines: (1) shared redaction and intent privacy repair, (2) bounded Library/Editor JSON interpretation, (3) aggregate saved-set descriptors and ID-only selection, (4) adversarial verification. No dependencies, desktop UI changes, live provider calls, audio writes or export changes. UI consent and stale-context handling belong to the integration slice. Rollback removes the optional entrypoints without affecting offline helpers.

## Success
Synthetic transport tests prove configured chat requests, strict bounded schemas, grounded references, default-off/no-key behavior and path redaction. Coordinator runs the release gate on integrated HEAD.
