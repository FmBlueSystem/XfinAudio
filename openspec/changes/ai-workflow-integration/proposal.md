# Approved AI workflow integration

Implement the reviewed Library, Create, Review, saved-playlist Editor, My Playlists,
Metadata, Live Assistant and Settings improvements while preserving the audited
local recommendation/export engine. The user approved this scope on 2026-09-30.

Out of scope: provider credential setup, live API use during development,
macOS packaging, tags/releases, merge/deployment, audio analysis expansion or live
Serato DB writes. Subsequent user authorization permits publishing a branch and
a draft GitHub PR after validation; it does not authorize merging or a release.

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

## Publication review chain

The final integration PR intentionally includes the earlier audited repairs plus
this AI workflow chain. It is not represented as a small PR. Individual local
commits are review slices, backed by the capability proposals and RED/GREEN
records; new AI slices remain within 400 changed lines. Review in order:

1. Audited security, immutable state, algorithms, Serato integrity and build gates
2. AI Settings and secure opt-in runtime boundary
3. Local Library/Create/Editor/saved-set workflows and shell reachability
4. Grounded Review/Live/Metadata evidence and request-context isolation
5. Optional structured remote interpreters and explicit-consent UI
6. Independent acceptance fixes, compact layouts, safe deletion, localization
7. Final verification evidence and candidate version alignment

An authenticated Git transport is unavailable in this execution environment. The
user's authorized GitHub connector may reconstruct the same ordered trees and
messages with new commit identities. Every tree must match exactly; the final
remote SHA is fetched independently and receives its own full gate and CI review.
Original local and remote SHA identities are reported separately. No remote
branch may be overwritten, and current main must be checked before publication.
