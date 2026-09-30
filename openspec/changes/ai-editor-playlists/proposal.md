# Offline conversational playlist workflows

## Intent and approval
Make saved playlists reachable in a draft editor and support safe local conversational edits and retrieval. Parent coordination records explicit user approval of all proposals on 2026-09-30.

## Scope and safety
Deterministic offline shortening and energy ordering, reviewable previews, explicit apply-to-draft, explicit Save, cancel, and grounded saved-set search/comparison. No provider calls, audio/metadata writes, fabricated facts, dependencies, or live Serato writes. Existing export safety remains authoritative. Locks preserve membership; energy ordering also preserves locked slots. Exclusions cannot re-enter a proposal. Unsupported requests are rejected visibly.

## Chained review plan
Each conventional commit is a sequential review slice capped at 400 changed lines:
1. SDD initialization
2. Pure deterministic edit engine and RED/GREEN tests
3. Draft editor controls and RED/GREEN widget tests
4. Coordinator preview/save/reorder safety and integration tests
5. Grounded retrieval/comparison engine and tests
6. My Playlists query UI wiring and widget tests
7. Additional adversarial regression verification and final evidence
Split any slice further before exceeding the cap. Shell navigation is integrated by the parent coordinator in a separate chain.

## Success and rollback
Saved playlists stay byte-for-byte logically unchanged until Save. Preview/apply never persists. Saved-set responses name only actual results, disclose missing metadata, and do not modify sets. Rollback by reverting this chain in reverse order.
