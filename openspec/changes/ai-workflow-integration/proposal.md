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
