# Specification: electron-playlist-improvement

## Status and evidence

This spec records the **as-built** Electron AI playlist-improvement behavior landed by
change `ai-playlist-improvement` (`openspec/changes/ai-playlist-improvement/`). It is
durable capability wording, not a plan.

Evidence is **offline only, with injected or mocked transports and a mocked provider**.
The referencing change's `verify-report.md` is the evidence of record: it records the
observed test runs and states explicitly that **real provider behavior, native
OS-dialog confirmation on macOS, and real-library acceptance remain pending** and are not
proven here. Provider-ready, visual, and live-library acceptance MUST NOT be claimed from
this spec.

This spec deliberately does not restate or weaken the older `my-playlists-screen`
capability (including its "Add from Library" wording) or the manual editor persistence
invariant; those remain owned by their own specs and by the source.

## Purpose

Define the bounded, opt-in AI improvement flow on the saved-playlist editor: a user
instruction produces a locally validated, token-only proposal whose ordered before/after
diff and assessment are previewed read-only, applied only to the in-memory draft, and
persisted only through a separate proposal-bound compare-and-update save. The manual
editor path keeps rejecting additions.

## Requirements

### Requirement: opt-in bounded candidate set

The improvement request SHALL authorize only tracks from a locally built candidate set
with explicit bounds: the open draft contributes `2..80` tracks (`MIN_IMPROVEMENT_TRACKS
= 2`, `MAX_DRAFT_TRACKS = 80`), replacement candidates are included only when the user
opts in for that request and are capped at `MAX_REPLACEMENT_CANDIDATES = 20`, and the
total never exceeds `MAX_CANDIDATES = 100`. A draft above the cap SHALL fail closed with
a clear message and MUST NOT be silently truncated.

#### Scenario: replacements are opt-in and bounded
- **GIVEN** an open draft within `2..80` tracks
- **WHEN** the user prepares an improvement with replacements disabled, then with
  replacements enabled against a larger pool
- **THEN** the authorized set contains the draft tokens and no replacement pool when
  disabled
- **AND** at most `20` replacement candidates when enabled
  (`tests/test_playlist_improvement.py::test_replacement_pool_is_empty_unless_opted_in`,
  `tests/test_playlist_improvement.py::test_replacement_pool_caps_at_twenty`,
  `tests/test_playlist_improvement.py::test_total_candidates_never_exceed_one_hundred`)

#### Scenario: the draft cap fails closed without truncation
- **WHEN** the open draft exceeds `80` tracks
- **THEN** the request fails before candidate allocation with a clear bounds message and
  the draft is not truncated
  (`tests/test_playlist_improvement.py::test_draft_above_cap_fails_closed_without_truncation`,
  `tests/test_headless_ai_context.py::test_editor_improvement_over_cap_draft_fails_before_candidate_allocation`)

### Requirement: request-scoped pseudonymous tokens

The provider SHALL receive only ephemeral `16`-hex tokens generated fresh per request
(`secrets.token_hex(8)`), unique within the request, never a stable path-derived id.
Tokens SHALL NOT be reused across requests, edit sessions, or surfaces, and the
reverse token→path map SHALL stay in local memory only. The disclosure SHALL state that
this is pseudonymization, not anonymity, because titles and metadata are still
transmitted.

#### Scenario: tokens are fresh, unique, and not stable across requests
- **WHEN** two improvement requests are prepared from the same draft and path
- **THEN** each request receives fresh unique `16`-hex tokens and no token repeats across
  requests
  (`tests/test_playlist_improvement.py::test_generated_tokens_are_16_lowercase_hex_and_unique`,
  `tests/test_playlist_improvement.py::test_same_draft_produces_fresh_tokens_per_request`,
  `tests/test_playlist_improvement.py::test_same_path_never_yields_a_stable_cross_request_token`)

#### Scenario: no stable identity or path reaches the provider
- **WHEN** the outgoing payload is built after consent
- **THEN** it carries tokens plus the disclosed bounded metadata and no filesystem path,
  `sha256(path)` id, credential, raw audio, or whole library
  (`tests/test_playlist_improvement.py::test_payload_discloses_only_bounded_fields_and_no_stable_identity`,
  `tests/test_ai_request_privacy.py::test_improvement_request_redacts_paths_and_sends_no_path_or_stable_id`)

### Requirement: exact disclosure before consent

Before any transmission, the app SHALL show the exact recipient, the exact bounded field
list, the exact draft count, whether replacement candidates are included and their exact
count, and the explicit statement that the identifiers are request-scoped random tokens.
The app SHALL NOT transmit until the user authorizes that specific request, and consent
SHALL also require the existing native OS confirmation before the provider call.

#### Scenario: prepare discloses and does not transmit
- **WHEN** an improvement instruction is prepared
- **THEN** the exact disclosure is produced and no provider request is made
  (`tests/test_headless_optional_ai.py::test_editor_improvement_prepare_discloses_without_contacting_provider`,
  `tests/test_headless_ai_context.py::test_editor_improvement_context_discloses_exact_counts_fields_and_pseudonyms`,
  `desktop-electron/tests/optional-ai-view.test.mjs` — "the editor improvement view states
  the instruction, the default-off replacement toggle and an accurate disclosure")

#### Scenario: declined confirmation never transmits or binds
- **WHEN** the user declines the request confirmation (or the native OS confirmation
  returns false)
- **THEN** no provider transmission occurs and no proposal is bound
  (`tests/test_headless_optional_ai.py::test_editor_improvement_denied_confirmation_never_transmits_or_binds`,
  `desktop-electron/tests/optional-ai-host.test.mjs` — "prepare and declined native AI
  confirmation cannot send a provider request")

#### Scenario: a new instruction discards prior disclosure and consent
- **WHEN** the instruction changes or a replacement toggle changes before authorization
- **THEN** previously prepared disclosure, tokens, and consent are discarded and cannot
  be reused by a later request or a different edit session
  (`desktop-electron/tests/optional-ai-view.test.mjs` — "toggling replacements discards
  pending disclosure and consent, then reprepares the exact improvement context")

### Requirement: bounded improvement instruction

The AI improvement instruction SHALL be bounded at `2000` characters across the
renderer prompt, the IPC bridge, and the backend validation. The legacy manual request
SHALL keep its existing `500`-character bound at the renderer input/UI only; the manual
IPC bridge (`security.ts` `previewPlaylistEdit`) and the headless backend
(`playlist_editor.py` `playlist.edit.preview`) accept up to `2000`, pre-existing and not
widened by this change. The AI bound MUST NOT widen the manual path, the manual command
MUST NOT be described as universally rejecting instructions above `500`, and there MUST
NOT be an end-to-end manual `500` bound claimed.

#### Scenario: improvement prompt is 2000 across all layers
- **WHEN** the improvement instruction and the legacy manual edit request are validated
- **THEN** the improvement instruction accepts up to `2000` characters in the renderer
  prompt, the IPC bridge, and the backend, while the legacy manual renderer input stays
  at `500` and the pre-existing manual IPC/backend request bound is `2000`
  (`src/xfinaudio/headless/ai_context.py` bound `> 2000`,
  `src/xfinaudio/ai/structured_common.py` bound `> 2000`,
  `desktop-electron/renderer/optional-ai-view.ts` `maxLength = 2000`,
  `desktop-electron/renderer/optional-ai.ts` `<= 2000`,
  `desktop-electron/src/security.ts` `Invalid AI request` above `2000` and
  `previewPlaylistEdit` edit request above `2000`,
  `src/xfinaudio/headless/playlist_editor.py` `playlist.edit.preview` `_text(..., 2000)`,
  `desktop-electron/renderer/editor.ts` manual request above `500`)

### Requirement: bounded token-only response

An accepted response SHALL be a strict object whose `orderedTrackIds` reference only
tokens from the authorized set for that request, with optional bounded `rationale`, and
SHALL stay inside the unchanged shared `4096`-character response bound. Any unknown or
out-of-scope token, duplicate, non-token member, malformed or oversized payload, path or
`sha256(path)` id, or non-object SHALL be rejected before any edit exists.

#### Scenario: out-of-scope and duplicate tokens produce no edit
- **WHEN** a response references an unknown token, an out-of-scope token, or a duplicate
  token
- **THEN** no proposal is produced and the draft is untouched
  (`tests/test_ai_structured_assists.py::test_improvement_rejects_tokens_outside_the_authorized_candidate_set`,
  `tests/test_playlist_improvement.py::test_validator_rejects_out_of_scope_token`,
  `tests/test_playlist_improvement.py::test_validator_rejects_duplicate_tokens`,
  `tests/test_headless_optional_ai.py::test_editor_improvement_invalid_token_responses_produce_no_edit`)

### Requirement: read-only before/after preview with assessment

A response that passes token, membership, and freshness validation SHALL produce a local,
read-only preview containing the current order ("before"), the proposed order ("after"),
and the existing musical assessment (readiness, score, warnings). The preview SHALL NOT
change the draft or the saved playlist, and missing or invalid metadata SHALL be reported
honestly rather than invented.

#### Scenario: preview renders before/after and assessment without mutating
- **WHEN** a validated preview is shown
- **THEN** numbered before/after rows, counts, and the assessment render and neither the
  draft nor the saved playlist changes until the user acts
  (`desktop-electron/tests/renderer.editor-view.test.mjs` — "a read-only improvement
  preview renders numbered before/after rows, counts and assessment and mutates only on
  click",
  `desktop-electron/tests/renderer.editor.test.mjs` — "improvement preview is read-only
  until an explicit apply")

### Requirement: explicit draft-only apply

Applying an accepted preview SHALL change only the in-memory draft and bind it to that
specific proposal (`proposalId` + `digest`). The saved playlist SHALL remain unchanged
until the separate explicit save.

#### Scenario: apply changes only the draft and binds the exact proposal
- **WHEN** the user chooses "Aplicar al borrador"
- **THEN** only the draft changes and it is bound to the exact proposal for the dedicated
  save
  (`tests/test_headless_optional_ai.py::test_editor_improvement_apply_previews_authorized_replacement_without_saving`,
  `desktop-electron/tests/renderer.editor.test.mjs` — "applying an improvement updates
  only the draft and binds the exact proposal for a dedicated save",
  `desktop-electron/tests/renderer.optional-ai-app.test.mjs` — "applying the improvement
  changes only the draft, labels the bound save and persists through the dedicated
  command")

### Requirement: separate proposal-bound compare-and-update save

Saving an applied improvement SHALL use the dedicated command
`playlist.edit.save_improvement` with
`{editId, name, proposalId, digest, draftIds}`. The backend SHALL re-check the edit
session, the saved revision, the proposal identity, the proposal digest, and the current
draft fingerprint, then persist exactly the previously validated order through the
existing atomic compare-and-update. A mismatch or stale revision SHALL fail closed with
no write.

#### Scenario: bound save persists exactly the validated order
- **WHEN** an applied, still-current improvement is saved
- **THEN** exactly the validated order is persisted through compare-and-update
  (`tests/test_headless_playlist_editor.py::test_dedicated_improvement_save_persists_exactly_the_validated_order`,
  `tests/test_playlist_improvement.py::test_proposal_digest_is_deterministic_and_covers_every_binding`)

#### Scenario: mismatched identity or digest writes nothing
- **WHEN** `proposalId`, `digest`, edit session, saved revision, or current draft does not
  match the bound proposal
- **THEN** the save fails closed and no write occurs
  (`tests/test_headless_playlist_editor.py::test_bound_save_rejects_mismatched_proposal_identity_without_write`,
  `desktop-electron/tests/editor-security.test.mjs` — "improvement save bridge accepts
  only the exact bounded proposal-bound shape",
  `desktop-electron/tests/workflow.integration.test.mjs` — "improvement save bridge routes
  only to its dedicated bound command and keeps manual editing unchanged")

### Requirement: stale changes revoke the binding

Any manual draft mutation after apply (reorder, remove, or instruction edit), a stale
saved revision, a discard, or opening another playlist SHALL revoke the proposal binding
and disable the improvement save until the user re-runs the proposal. A late or stale
result SHALL never overwrite a newer draft.

#### Scenario: a manual mutation after apply invalidates the improvement save
- **WHEN** the draft changes after an improvement was applied
- **THEN** the bound save is disabled and no improvement write occurs
  (`tests/test_headless_playlist_editor.py::test_manual_reorder_save_after_binding_invalidates_the_improvement`,
  `desktop-electron/tests/renderer.editor.test.mjs` — "opening, discarding or resetting the
  editor revokes the improvement binding")

#### Scenario: stale context or stale result never binds
- **WHEN** the saved revision or library state changed, or a late result arrives for an
  older draft
- **THEN** the apply is refused or the newer draft is preserved, with no write
  (`tests/test_headless_optional_ai.py::test_editor_improvement_stale_revision_never_binds`,
  `desktop-electron/tests/renderer.optional-ai-app.test.mjs` — "a stale editor improvement
  payload is refused with an error and never changes or saves the draft",
  `desktop-electron/tests/renderer.editor.test.mjs` — "a late improvement result never
  overwrites a newer draft")

### Requirement: manual save still rejects additions

The ordinary manual editor path (`playlist.edit.save`, `PlaylistEditor._paths`, and
`validate_edit`) SHALL remain unchanged. The manual save MUST still reject unknown or
duplicate additions, and the improvement path MUST NOT route through it.

#### Scenario: manual save cannot add tracks
- **WHEN** a draft containing an addition is saved through the ordinary manual command
- **THEN** the save is rejected and no write occurs
  (`tests/test_playlist_improvement.py::test_manual_save_path_still_rejects_additions`,
  `desktop-electron/tests/renderer.editor.test.mjs` — "the ordinary save stays identical
  when no improvement is bound",
  `desktop-electron/tests/renderer.editor.test.mjs` — "a failed improvement save keeps the
  bound draft and never falls back to the manual save")

### Requirement: no automatic request, apply, or save

Typing, preparing, previewing, opening, renaming, or rendering SHALL NOT trigger a
provider transmission, a draft change, or a save. Each of request, apply, and save
remains an explicit user action.

#### Scenario: no side effects without an explicit action
- **WHEN** the user types, prepares, previews, cancels, or opens without choosing
  request/apply/save
- **THEN** no provider call, draft mutation, or save occurs
  (`tests/test_headless_optional_ai.py::test_editor_improvement_prepare_discloses_without_contacting_provider`,
  `desktop-electron/tests/renderer.optional-ai-app.test.mjs` — "editor improvement Apply
  stages a local preview from the exact ordered selector without touching the draft or the
  legacy request")

### Requirement: editor-local policy, not global widening

Token format, candidate caps, payload budget, the improvement schema, and any per-request
model choice SHALL be editor-local. The shared `_POLICY`, the shared `4096`-character
response bound, the shared request byte bound, and the global default model for other
surfaces SHALL NOT be widened.

#### Scenario: shared policy and bounds stay unchanged
- **WHEN** the editor improvement call is built
- **THEN** it uses its own schema and token bounds while other surfaces keep the shared
  policy, response bound, request byte bound, and default model
  (`tests/test_ai_structured_assists.py::test_improvement_prompt_replaces_the_shared_no_selection_policy`,
  `tests/test_ai_structured_assists.py::test_improvement_payload_sends_only_bounded_candidate_metadata`)

### Requirement: offline editor path remains usable

When AI is disabled, unconfigured, unavailable, invalid, or the draft is out of bounds,
the existing deterministic local editor path SHALL remain usable and the AI surface SHALL
be withheld rather than falling back to a widened request.

#### Scenario: unusable AI or out-of-bounds draft offers no AI surface
- **WHEN** the AI is unavailable or the draft is outside `2..80`, or the improvement save
  bridge is absent
- **THEN** the editor stays usable and no legacy `editId`-only AI request replaces the
  improvement surface
  (`desktop-electron/tests/renderer.optional-ai-app.test.mjs` — "an editor draft outside
  the improvement bounds offers no AI surface instead of the legacy editId request",
  `desktop-electron/tests/renderer.optional-ai-app.test.mjs` — "a bridge without the
  improvement save route disables the editor AI surface safely",
  `tests/test_headless_optional_ai.py::test_legacy_editor_four_operation_apply_is_unchanged`)

## Non-claims and pending acceptance

Recorded here so this spec is not read as more than it is:

- **Real provider acceptance is pending.** All provider interaction was exercised with an
  injected or mocked transport. No credential, network, or live model call was performed.
- **Native OS-dialog acceptance is pending.** The macOS confirmation dialog is exercised
  through a mocked `confirm` dependency; the visible system dialog was not observed.
- **Visual macOS and installed-app acceptance are pending.** The renderer was exercised
  through a mocked DOM; no visible macOS rendering was observed.
- **Real-library acceptance is pending.** No real music library was scanned or disclosed.
- **Tokenization is pseudonymization, not anonymity.** Titles, artists, and bounded
  metadata are transmitted after consent.
- The saved-editor surface has no lock or exclude controls; nothing here claims to
  preserve or enforce locked or excluded tracks on that surface.
