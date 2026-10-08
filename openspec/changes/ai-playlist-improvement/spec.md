# Observable requirements

Behavior-only statements. Implementation detail lives in `design.md`. This revision
reflects the documented challenge corrections: ephemeral provider tokens instead of
`sha256(path)` ids, explicit caps that fit the unchanged response bound, a dedicated
proposal-bound save for replacements, current-draft freshness, and no asserted
locks/excludes on the saved-editor surface.

- **R1 — Instruction on an existing playlist.**
  GIVEN a saved playlist is open in the editor with at least two tracks and no more
  than the supported draft bound,
  WHEN the user types an improvement instruction and asks for a proposal,
  THEN the app accepts the bounded instruction and prepares a proposal for that same
  playlist draft, without yet transmitting anything and without changing the draft.

- **R2 — Exact disclosure before authorization.**
  GIVEN a prepared improvement instruction,
  WHEN the app is about to ask for authorization,
  THEN it shows the exact recipient, the exact bounded set of metadata fields, the
  exact count of draft identifiers, whether replacement candidates are included and
  their exact count, and the explicit statement that the identifiers are ephemeral
  random tokens with meaning only inside this request,
  AND it does not transmit until the user authorizes that specific request.

- **R3 — No disclosure without request-specific consent.**
  GIVEN a prepared instruction that the user has not authorized,
  WHEN any other action or a different instruction occurs,
  THEN no provider transmission happens,
  AND previously prepared disclosure, tokens, and consent are discarded and cannot be
  reused by a later request or a different edit session.

- **R4 — Only bounded authorized metadata is transmitted.**
  GIVEN the user authorized a specific request,
  WHEN the app builds the outgoing payload,
  THEN the payload contains only the bounded instruction text plus, for each authorized
  candidate, an ephemeral token and the disclosed metadata fields, and nothing else,
  AND it never contains filesystem paths, `sha256(path)` ids, raw audio, credentials,
  the whole library, or any candidate outside the request-scoped set,
  AND the payload stays within a fixed byte budget below the shared request bound.

- **R5 — Token-only response.**
  GIVEN an authorized request has been sent,
  WHEN a response is accepted,
  THEN the response may reference tracks only through ephemeral tokens that belong to
  the authorized candidate set for that request,
  AND any other field, path, title-based selection, or free-form instruction is not
  treated as an edit.

- **R6 — Invalid, stale, or out-of-scope responses produce no edit.**
  GIVEN a response that is malformed, oversized, duplicated, references an unknown or
  unauthorized token, omits required tokens, contains unsupported changes, exceeds an
  explicit bound, or no longer matches the open session, the saved revision, or the
  current renderer draft order,
  WHEN the app validates it,
  THEN it produces no proposal, leaves the draft untouched, and reports a clear,
  non-technical message,
  AND no partially validated edit is ever applied.

- **R7 — Local before/after diff and assessment.**
  GIVEN a response that passes token and freshness validation,
  WHEN the app builds the local preview,
  THEN the user sees the current order ("before"), the proposed order ("after"), and
  the existing musical assessment for the proposed order,
  AND missing or invalid metadata is reported honestly rather than invented.

- **R8 — Draft apply only; save stays explicit.**
  GIVEN a validated local preview,
  WHEN the user chooses to apply it,
  THEN only the in-memory draft changes and the draft becomes bound to that specific
  validated proposal,
  AND the saved playlist is unchanged until the user performs the separate, explicit
  save action.

- **R9 — No automatic request, apply, or save.**
  GIVEN any editor state,
  WHEN the user has not explicitly authorized a request, chosen to apply a preview, or
  chosen to save,
  THEN no provider transmission, draft change, or save occurs as a side effect of
  typing, preparing, previewing, opening, renaming, or rendering.

- **R10 — Manual path and persistence invariants are preserved.**
  GIVEN the feature is active,
  WHEN drafts and saves are handled,
  THEN no audio file is modified and no live Serato database V2 is written,
  AND the ordinary manual save still rejects unknown or duplicate additions through
  `validate_edit`,
  AND the save path remains an atomic compare-and-update that refuses a stale revision.

- **R10a — No asserted locks or excludes.**
  GIVEN the saved-playlist editor has no lock or exclude controls,
  WHEN the app describes or validates a draft, manual or AI,
  THEN it does not claim to preserve, inherit, or enforce locked or excluded tracks on
  that surface,
  AND the AI validator enforces only membership, uniqueness, explicit bounds, and
  exact-order binding.

- **R11 — Dedicated proposal-bound exact-order save.**
  GIVEN a draft that was produced by applying a validated improvement preview,
  WHEN the user explicitly saves it,
  THEN the app persists exactly the previously validated order through a dedicated
  proposal-bound command that re-checks the proposal identity, digest, edit session,
  saved revision, and current draft match,
  AND an ordinary manual save remains incapable of adding tracks,
  AND any manual mutation after apply, any stale revision, or any mismatched proposal
  fails closed with no write.

- **R12 — Current draft order is part of freshness.**
  GIVEN the user changes the unsaved draft order after preparing or receiving a
  proposal,
  WHEN the app re-validates the submitted draft snapshot or the renderer reports a
  local draft mutation,
  THEN the prepared proposal is treated as stale, no preview or apply is offered, and
  the user can retry from the current draft,
  AND freshness is evaluated over the draft snapshot the client actually submits, never
  over a client-only edit the backend was not told about.

- **R13 — Explicit conservative bounds, fail closed.**
  GIVEN an instruction, a draft, a replacement pool, or a response,
  WHEN either is processed,
  THEN each has an explicit local limit: instruction length, draft track count
  (default maximum 80), replacement candidate count (default maximum 20), total
  candidate count (default maximum 100), token length, payload bytes, and accepted
  response size,
  AND a playlist larger than the draft bound fails closed with a clear message and the
  draft is never silently truncated.

- **R14 — The offline editor keeps working without AI.**
  GIVEN AI is disabled, unconfigured, unavailable, or the request is invalid,
  WHEN the user asks for a proposal,
  THEN the existing deterministic local proposal and assessment path still works and
  the editor remains usable.

- **R15 — Retry and recovery.**
  GIVEN a failed, cancelled, or rejected request,
  WHEN the user returns to the editor,
  THEN the instruction and the draft are preserved, a retry is reachable, and no
  expired token, consent, or result can be re-applied.

- **R16 — Editor-specific policy, not global widening.**
  GIVEN the improvement schema, prompt policy, token format, or any per-request model
  selection,
  WHEN the app builds the provider call,
  THEN those choices apply only to the editor improvement request,
  AND the shared response bound, shared `_POLICY`, shared request byte bound, and the
  global default model for other surfaces are unchanged.

- **R17 — Honest disclosure of pseudonymization.**
  GIVEN the disclosure preview,
  WHEN it is shown,
  THEN it states that titles, artists, and bounded metadata are transmitted, that the
  tokens are random per-request pseudonyms rather than anonymous identities, and that
  no paths, `sha256(path)` ids, credentials, or audio are sent.

## As-built evidence (2026-10-04/05)

The requirements above state the intended behavior; this note records what has actually
been observed, without claiming live acceptance.

- Local, mocked-transport implementations landed in I1 (`56c491c`, `75a11a2`,
  `7dadafb`, `1297e12`, `4707dbd`), I2 (`38dbcc6`, `6733dff`, `235caae`), and I3
  (`f60f81b`, `7aef8b9`, `a8ccb5a`, `a74bbed`, `e9bccb9`), with ODD-task documentation
  closure `4533422`.
- The independent offline gate and commit evidence is recorded once in
  `verify-report.md`.
- R4, R5, R6, R9, and R16 were exercised only with injected or mocked transports. No
  live provider, credential, network, real library, installed app, or visual macOS
  confirmation was observed, so provider readiness and native acceptance are not
  proven.
- The AI improvement instruction bound (R13) is 2000 characters across renderer,
  bridge, and backend. The legacy manual request is bounded at 500 only at the renderer
  input/UI; the IPC bridge (`security.ts` `previewPlaylistEdit`) and the headless
  backend (`playlist_editor.py` `playlist.edit.preview`) already accepted up to 2000
  before this change. The manual command does not universally reject instructions above
  500, there is no end-to-end manual 500 bound, and this change did not widen or narrow
  those pre-existing 2000 bounds.
- R11's dedicated save command is `playlist.edit.save_improvement` with
  `{editId, name, proposalId, digest, draftIds}`; the ordinary `playlist.edit.save`
  path is unchanged and still rejects additions.
- Acknowledged native receipts exist only for the documentation chain `4533422..88ab13a`
  (`review-c9c388e5ff8775f0`), I3 U1 `f60f81b` (`review-3eca483813fe5bd4`), and I3 U2
  `7aef8b9` (`review-f141608a936191bd`); the `7aef8b9..a74bbed` slice stopped unapproved
  at lineage `review-c5bd20ee943fbd91` (`native_stop_required`/`unknown_causality`), and
  the I1, I2, first-docs `7d381ae`, and U4b `e9bccb9` slices have no receipt. Clone-local
  RDD is off by explicit user choice; that waives the pending native review but is never
  feature-level or delivery approval. Field acceptance remains pending.
- I4's durable `openspec/specs` reconciliation is recorded in
  `openspec/specs/electron-playlist-improvement/spec.md`. Live provider and visual
  validation remain pending.
