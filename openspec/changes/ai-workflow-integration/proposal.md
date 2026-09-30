# Approved AI workflow integration

Implement the reviewed Library, Create, Review, saved-playlist Editor, My Playlists,
Metadata, Live Assistant and Settings improvements while preserving the audited
local recommendation/export engine. The user approved this scope on 2026-09-30.

Out of scope: provider credentials, live API use during development, GitHub
publication, macOS packaging, audio analysis expansion or live Serato DB writes.

## Chained review plan (each implementation slice <=400 changed lines)

1. Settings: explicit runtime opt-in, disclosure and connection-test lifecycle
2. Library: deterministic language-to-editable-filter interpretation
3. Create: interpreted request preview and confirmed local generation
4. Playlists: descriptive retrieval/comparison and editor proposals
5. Review: identity-bound narration and grounded alternative facts
6. Live: real engine ranking and readiness contract
7. Metadata: deterministic repair priorities/explanations
8. Shell: editor/Live/Configure AI wiring and lifecycle integration
9. Acceptance: screen interaction matrix, offscreen captures, final release gate

Each branch records its RED/GREEN evidence and commits reviewable slices; this
integration change owns cross-screen behavior and packaging. No PR is published.
Rollback is a local revert of the relevant chained commits.

Success: all screen workflows are reachable, cancellable and honest about data,
local functionality works offline, no metadata is fabricated, and the exact
packaged SHA passes the project's configured gate.

## Approved AI interpretation completion

The reviewed AI opportunities require actual optional provider interpretation,
not a relabeling of bounded local heuristics. Additional chained slices add:

10. Strict, privacy-minimized remote Library/Editor/saved-set intents; local
    fallbacks remain honestly labeled and engine validation remains authoritative
11. Optional grounded Metadata/Live commentary from already-computed evidence,
    with explicit consent, cancellation and no effect on tags or ranking
12. Shared async UI, context/request guards, payload adversarial tests and renewed
    independent acceptance. No live API validation or credential setup is added.
