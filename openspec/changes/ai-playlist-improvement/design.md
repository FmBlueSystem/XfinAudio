# Design

## Current state (read before designing)

The behavior already exists in pieces; this change connects them without widening
authority. This revision is grounded in source read after an independent read-only
challenge disproved six earlier assumptions (see `proposal.md` "Correction notice").

- `src/xfinaudio/application/playlist_edit_intents.py` — `propose_edit()` and
  `validate_edit()`. `validate_edit` rejects any candidate multiset that exceeds the
  source multiset ("A draft cannot add unknown or duplicate tracks") and accepts
  optional `locked_paths`/`excluded_paths`. The saved editor never passes those
  arguments, so it has no lock/exclude behavior.
- `src/xfinaudio/application/playlist_edit_assessment.py` — `assess_playlist_edit()`
  scores an exact order with the existing local engine and raises on missing/invalid
  BPM, energy, or Camelot key. It is the honest musical assessment.
- `src/xfinaudio/headless/playlist_editor.py` — `PlaylistEditor` owns opaque edit
  sessions. `EditSession.paths_by_id` maps the draft's `_public_track` ids
  (`sha256(path)`, 64 hex) to paths. `execute()` handles `playlist.edit.open/preview/
  save/discard`. `save` calls `_paths()` first: `_paths` requires 64-char ids, resolves
  them through `session.paths_by_id`, and then calls
  `validate_edit(session.original.track_paths, paths)`. **That call rejects any
  addition even if `paths_by_id` contained the extra ids.** Save then uses
  `compare_and_update(session.original, ...)` for an atomic compare-and-update, and
  `_current()` re-checks `session.edit_id` and `_revision()`.
- `src/xfinaudio/headless/common.py` — `_public_track()` sets
  `id = sha256(track.path)`. Deterministic and verifiable offline; a pseudonym, not
  anonymity.
- `src/xfinaudio/headless/optional_ai.py` — `OptionalAI` implements `ai.prepare`,
  `ai.confirmation`, `ai.run` (native confirm then transmit), and `ai.apply`.
  `_pending`/`_fresh` pin the reference, settings revision, credential binding, and
  context fingerprint; `invalidate()` drops consent. `ai.run` requires
  `confirmed is True`.
- `src/xfinaudio/headless/ai_context.py` — `build_context()` builds immutable, bounded
  assistance scopes and disclosure lines. The `editor` surface currently fingerprints
  only `[session.edit_id, session.revision]` plus library records and discloses "Solo
  tu petición de edición, sin rutas." It does **not** include the renderer's unsaved
  draft order.
- `src/xfinaudio/headless/ai_execution.py` — `execute_context()` runs the language
  service; `apply_context()` produces local, applyable data. The `editor` branch calls
  `interpret_editor_request()` and returns `{"request": command}`.
- `src/xfinaudio/ai/structured_common.py` — `ask_object()`/`strict_object()` enforce a
  path-redacted request, a **4096-character response bound**, unique keys,
  object-only responses, and reject `NaN`/`Infinity`/duplicate keys. `_POLICY` is
  shared by every surface.
- `src/xfinaudio/ai/structured_assists.py` — `interpret_editor_request()` returns the
  bounded four-operation `EditorInterpretation`. This stays for the offline path.
- `src/xfinaudio/headless/ai_transport.py` — `provider_request()` binds every surface
  to `DEFAULT_MODEL` and `MAX_REQUEST_BYTES = 64 * 1024`.
- `src/xfinaudio/ai/privacy.py` — `redact_paths()` is the path-minimization primitive.
- `desktop-electron/renderer/editor.ts` — `SavedPlaylistEditor` keeps `base`/`draft`,
  has `previewPlaylistEdit`/`applyPreview`/`save`/`discard`, a `generation` guard for
  late responses, and `updateTracks()` that only replaces the draft array. It holds no
  authorization state and cannot authorize additions; the backend save is the
  authority. The legacy manual instruction input there is bounded at 500, while the
  manual preview bridge in `security.ts` and the headless `playlist.edit.preview`
  backend accept up to 2000; those 2000 bounds pre-existed this change.
- `desktop-electron/renderer/optional-ai.ts` — `OptionalAiController` owns consent,
  `prepare`/`ask`/`applySuggestion`, and strict response copying (`recordCopy`,
  `localApplyCopy`).
- `desktop-electron/renderer/app.ts` — `syncAiContext()` already publishes surface
  `editor` with `{editId}`, and its renderer-local revision key already includes
  `editor.draft.tracks.map((track) => track.id)`. `planAiApply('editor', ...)`
  currently accepts only `{request}` and calls `editor.setRequest(request)`.
- `desktop-electron/src/security.ts` — `validateEditorRequest()` bounds `editId` to a
  UUID, `trackIds` to `<=500` 64-hex ids each, and the preview request to `<=2000`
  characters with no control characters. `validateAiRequest()` requires the editor AI
  context keys to be exactly `editId`.
- `desktop-electron/src/optional-ai-host.ts` — the only native confirmation surface;
  `ask()` performs the system confirmation before `ai.run`.

## Architecture and ownership

Four independently reviewable units, one authority chain:

1. **Local candidate, token, and validation core (I1, Python).** A new pure module plus
   a narrow extension of `PlaylistEditor`. It owns ephemeral token generation, the
   authorized candidate set, the dedicated token-only validator, token→path
   resolution, the proposal binding, the proposal-bound save authorization, and
   stale/CAS rejection. It never calls a transport.
2. **AI proposal and disclosure boundary (I2, Python).** `OptionalAI`, `ai_context`,
   `ai_execution`, and `structured_assists` own the strict response schema, the
   bounded token/metadata disclosure, draft-order freshness, the editor-specific
   schema policy, and per-request confirmation. It only calls the injected transport.
3. **Editor review wiring (I3, Electron renderer).** `editor.ts`, `editor-view.ts`,
   `optional-ai.ts`, and `app.ts` own instruction capture, the readable diff, the local
   preview, draft-only apply, the proposal-bound save routing, and the separate manual
   Save.
4. **Verification and durable-spec reconciliation (I4).** Offline gates, structural
   checks, and recording the new editor behavior in the durable capability wording.

The renderer never resolves paths and never decides authority; it only displays data
the backend validated and routes a save to the backend command the backend authorized.

## Data and behavior contracts

### Ephemeral provider tokens (replaces `sha256(path)` ids)

The provider must not receive `sha256(path)` ids because they are deterministic and
offline-verifiable. For one request only, the backend generates a fresh token for every
authorized candidate:

- `MAX_TOKEN_LENGTH = 16` lowercase hex characters (64 random bits), generated with
  `secrets.token_hex(8)`.
- Tokens are unique inside a request; a collision is regenerated, never resolved by
  first-wins.
- The token→path map is held only in local memory for the life of the request and its
  proposal. It is never persisted, logged, sent to the renderer as a path map, reused
  across requests, edit sessions, or surfaces, and it is discarded by `invalidate()`,
  discard, or save.
- The renderer continues to use the existing 64-hex `_public_track` ids for its own
  draft. The backend maps those draft ids and the pool paths onto ephemeral tokens
  before building the provider payload and keeps the reverse map local.
- Tokens are disclosed as pseudonyms: the disclosure states that titles/artists are
  still transmitted, so the request is not anonymous.

### Authorized candidate set

Built locally for one request, in the backend, from existing local state only:

- **Draft members** — every id of the open `EditSession` in the current renderer draft
  order. Always authorized. Bounded by `MAX_DRAFT_TRACKS = 80`; a larger open draft
  fails closed with `ai_context_too_large` and the draft is never silently truncated.
- **Replacement pool (opt-in, per request)** — a bounded set of already-scanned
  `TrackRecord`s, excluding any path already in the draft and excluding
  `excluded_paths` if the caller ever supplies them (it does not today). Capped at
  `MAX_REPLACEMENT_CANDIDATES = 20`. Selected by a deterministic local key (for
  example harmonic/tempo proximity to the draft) so the set is reproducible and
  inspectable. Included only when the user enables replacement candidates for that
  request; when disabled the pool is empty.
- `MAX_CANDIDATES = MAX_DRAFT_TRACKS + MAX_REPLACEMENT_CANDIDATES = 100`.

The set is materialized as an immutable `candidates_by_token` mapping (ephemeral token
→ resolved path plus disclosed metadata fields). It is session-scoped and
request-scoped; it is never persisted and never widened between prepare and apply.

### Outgoing payload (bounded, path-free, token-only)

- The user instruction after `redact_paths(request, known_paths)`.
- For each authorized candidate, only the allowed display fields: ephemeral `token`,
  `title`, `artist`, `genre`, `bpm`, `key`, `energy`, `duration`, `status`,
  `missingFields`. No `path`, no `sha256(path)` id, no audio, no codec/bitrate, no
  library corpus.
- Bounds: instruction `<=2000` characters (existing `ask_object`), pool `<=20`, total
  candidates `<=100`, candidate fields bounded per field, and a stricter
  editor-specific payload budget
  `MAX_IMPROVEMENT_PAYLOAD_BYTES = 32 * 1024` checked before send and kept below the
  unchanged shared `MAX_REQUEST_BYTES = 64 * 1024`.
- The disclosure states the exact counts, the field list, token semantics, and the
  replacement on/off decision.

### Incoming response schema (token-only, fits the unchanged bound)

Strict JSON object, validated by a `_StrictImprovement` Pydantic model with
`extra="forbid"`, `strict=True`, `allow_inf_nan=False`, and a `model_validator`:

```json
{ "orderedTrackIds": ["<16-hex ephemeral token>", "..."], "rationale": "<optional, <=400 chars>" }
```

- `orderedTrackIds` is required, a non-empty list, length `<= min(100, |authorized|)`,
  each item exactly 16 lowercase hex, unique.
- `rationale` is optional, a string without control characters, `<=400` characters.
- Any other key, a non-object, a path-like string, a 64-hex string, `NaN`/`Infinity`,
  duplicate keys, or a payload over the existing 4096-character bound is rejected by
  `strict_object`/the model before any local edit exists.
- **Bound arithmetic that makes this fit.** The worst case is `MAX_CANDIDATES = 100`
  tokens: 100 × (`"` + 16 + `"` + `,`) ≈ 1,900 characters for the list, plus the
  `{"orderedTrackIds": ... ,"rationale":"..."}` envelope and a 400-character rationale,
  for roughly 2,340 characters total. This stays inside the unchanged 4096-character
  bound without widening it globally for other surfaces. The earlier 64-hex design
  could not: 64-hex ids plus punctuation are roughly 67 characters each and fail above
  about 55 tracks.
- Unknown tokens are rejected at the boundary and again at authorization time; the
  schema alone cannot prove membership, so membership is a local check.

### Dedicated local validator

New pure function `validate_improvement_proposal(source, authorized_tokens, ordered,
*, max_total, max_additions)`:

- every token in `ordered` belongs to `authorized_tokens` (rejects unknown/out-of-scope
  tokens);
- no duplicates;
- `source` and `ordered` are non-empty and bounded by `max_total`;
- additions beyond the source are all pool tokens and number `<= max_additions`;
- the resulting count is `>= MIN_IMPROVEMENT_TRACKS = 2` and `<= MAX_DRAFT_TRACKS`;
- every source path is either retained or replaced by an authorized pool path; nothing
  else is invented.

It returns the resolved ordered paths (tokens → paths through `candidates_by_token`
only). It is deliberately separate from `validate_edit`, which keeps rejecting
additions for the manual path. It does **not** enforce locks or excludes, because the
saved-editor surface has none; claiming otherwise would be false.

### Proposal binding and dedicated exact-order save

Because `playlist.edit.save` rejects additions, a replacement order needs its own
authorization. After validation, the backend stores an `ImprovementProposal` in the
single editor session:

- `proposal_id` (uuid4), `edit_id`, `source_revision`, `draft_fingerprint`,
  `before_paths` (exact), `candidates_by_token` (immutable local map),
  `after_paths` (resolved, validated), and a
  `digest = sha256(canonical json of [edit_id, source_revision, draft_fingerprint,
  before_paths, after_paths, sorted token→path pairs])`.

The draft apply binds the renderer draft to `proposal_id` + `digest`. Saving a bound
draft uses the **dedicated command** `playlist.edit.save_improvement` with
`{editId, name, proposalId, digest, draftIds}`. `draftIds` is the bounded ordered list of
public draft identities (`2..80`, unique), used only to recompute the draft fingerprint;
the renderer still sends no raw path list on this command, so it cannot smuggle tracks.
The backend:

1. re-checks `_current(editId)` (edit session plus saved `_revision`);
2. recomputes the current draft fingerprint from the renderer-supplied current draft
   order and requires it to equal `draft_fingerprint`;
3. requires `proposal_id` and `digest` to match the stored proposal;
4. re-runs `validate_improvement_proposal` against the stored authorized set;
5. calls `compare_and_update(session.original, name=name, track_paths=after_paths)`
   and fails closed on `None` with `stale_edit`.

The ordinary `playlist.edit.save` command, `_paths`, and `validate_edit` are unchanged,
so the manual path still rejects additions. Any manual mutation after apply
(`move`/`remove`/instruction edit) invalidates the proposal binding and disables the
improvement save until the user re-runs the proposal or discards; this is fail-closed
and prevents a widened save from outliving its authorization.

### Draft-order freshness in context

`build_context(surface="editor")` is extended to include the current renderer draft
order in the selector and in `revision_data`:

- the renderer sends the ordered draft ids (its existing 64-hex ids) alongside
  `editId`; the backend bounds the list (`2..80`), requires uniqueness, and requires
  every id to exist in `session.paths_by_id`, so the renderer cannot smuggle an
  unauthorized id;
- the backend adds `draft_fingerprint = sha256([edit_id, source_revision, ordered
  draft ids])` and includes it in the context revision.
- `_fresh()` rebuilds from the **frozen selector**, so it validates saved/library
  state and the submitted draft snapshot, not independent client-only edits after
  prepare. Random per-request tokens must never enter `revision_data`: preparing
  creates one candidate/token snapshot, and run/apply retain that same mapping after
  the stable `_fresh()` comparison.
- The renderer must invalidate the pending AI preview on every local draft mutation
  and submit a new ordered draft for any later prepare. The backend must compare the
  exact submitted draft with the proposal at bind and save; it cannot observe a
  client-only edit unless the client updates or revokes its context. A stronger
  server-enforced live-draft guarantee would require a separate server-side draft
  revision signal and is not inferred from `_fresh()` alone.

This binds AI to a submitted unsaved-draft snapshot without claiming that the
backend can observe unreported client-only changes.

### Local preview payload

`apply_context`/the editor path returns, after validation and freshness checks:

```
{ surface: "editor",
  data: { proposalId, digest, sourceRevision, before: [{id,title,artist,bpm,key,energy,missing}],
          after: [ ... same shape ... ],
          assessment: { description, readiness, qualityScore, warnings },
          addedIds: [...], removedIds: [...] } }
```

The renderer validates this shape, stores the local `EditPreview` plus the
`proposalId`/`digest` binding, and the user's existing "Aplicar al borrador" action
performs `updateTracks`. Save then routes to the proposal-bound command while the
binding is valid, and to the unchanged manual command otherwise.

### Freshness and CAS

- `session.edit_id`, `_revision(playlist)`, the candidate-set digest, and the current
  draft fingerprint are re-checked when the candidate set is built, after the model
  response, and before returning the preview/apply/save.
- `OptionalAI._fresh(reference)` re-builds the context and compares the fingerprint,
  the settings revision, and the credential binding before send and after receive.
- `compare_and_update` still guards the actual save.
- Any mismatch yields `stale_edit`/`stale_ai` and produces no edit.

### Editor-specific policy, not global widening

- `_POLICY` and `strict_object`'s 4096-character bound stay unchanged for all surfaces.
  The improvement schema text is composed only in the editor improvement call
  (`interpret_improvement_request` or equivalent), never appended to the shared
  `_POLICY`.
- Token format, caps, payload budget, and response-size expectations are editor-local
  constants.
- If a different model or policy is required, it is selected per request through the
  editor improvement call only. `provider_request`/`request_context` keep binding every
  other surface to the existing `DEFAULT_MODEL`, and `_resolve_model` is not changed to
  a global new default.
- The editor surface keeps its existing 30-second timeout entry in
  `AI_REQUEST_TIMEOUT_SECONDS`.

### Canonical instruction bound (as built)

**AI improvement prompt — 2000 characters across all three layers.** Renderer:
`optional-ai-view.ts` (`maxLength = 2000`) and `optional-ai.ts` (`<= 2000`). IPC bridge:
`security.ts` `validateAiRequest` rejects a request above 2000. Backend: `ai_context.py`
(`len(request) > 2000`) and `ask_object` in `structured_common.py` (`> 2000`).

**Legacy manual request — 500 only at the renderer input/UI.** `editor.ts` and
`editor-view.ts` bound the manual instruction at 500. The IPC bridge (`security.ts`
`previewPlaylistEdit`) and the headless backend (`playlist_editor.py`
`playlist.edit.preview`) already accepted up to 2000 characters before this change; I3
neither raised nor lowered them. The manual command therefore does not universally
reject instructions above 500, and there is no end-to-end manual 500 bound. The earlier
plan to align the manual renderer input to 2000 was not implemented, and this revision
records the observed split rather than the plan.

## The no-new-path invariant: explicit decision

The manual editor contract (`validate_edit`, `PlaylistEditor._paths`) rejects any path
outside the draft. Concrete *substitutions* require a candidate that is not in the
draft, so this change splits the invariant instead of silently relaxing it:

- **Manual path:** unchanged. Reorder/remove only; `validate_edit` still rejects
  additions; `_paths` still resolves only `paths_by_id`; `playlist.edit.save` cannot
  persist an addition.
- **AI path:** additions are permitted only when the token (a) exists in the
  request-scoped authorized candidate set, (b) was disclosed before consent, (c)
  passes `validate_improvement_proposal`, and (d) is saved through the dedicated
  proposal-bound exact-order command for the current draft and revision. Paths are
  still never accepted from the provider; only ephemeral tokens are, and the server
  resolves them locally.

Net effect: "no path outside the authorized candidate set, and no replacement persisted
without its exact proposal binding". This is narrower than an open add-from-library
feature and wider than the current manual draft. It is recorded in the durable
`openspec/specs/electron-playlist-improvement/spec.md` capability (I4.3), which does not
rewrite `my-playlists-screen/spec.md` and does not claim that spec's absent
add-from-library feature shipped.

## Alternatives considered

1. **Reuse the four-operation interpretation only.** Rejected: it cannot satisfy the
   user's chosen outcome of concrete track/ordering proposals.
2. **Widen `paths_by_id` and let `playlist.edit.save` accept additions.** Rejected:
   `validate_edit` rejects additions regardless of the map, and a general widened save
   would relax the manual invariant for every caller.
3. **Let the provider return paths or names.** Rejected: names are ambiguous and paths
   are sensitive; token-only plus server-side resolution is the only safe contract.
4. **Keep `sha256(path)` ids for the provider.** Rejected: deterministic,
   offline-verifiable, and correlatable across requests.
5. **Raise the shared 4096-byte response bound to fit 64-hex full orders.** Rejected:
   it would widen every surface. Compact tokens plus conservative caps keep the
   improvement path inside the existing bound.
6. **Send the whole scanned library.** Rejected: violates minimization and the
   request-scoped consent requirement.
7. **Apply the AI result straight to the draft.** Rejected: R7/R8 require a local
   before/after preview and a separate apply, and R9 forbids implicit change.
8. **A new parallel protocol method instead of the `editor` AI surface.** Rejected: it
   would duplicate consent, freshness, and native-confirmation machinery that
   `OptionalAI`/`OptionalAiHost` already own. A new save command is still required, but
   only for exact-order persistence.

## Affected files

### Landed in I1

New:

- `src/xfinaudio/application/playlist_improvement.py` — token generation, candidate
  selection, strict proposal model helpers, `validate_improvement_proposal`, and the
  `ImprovementProposal` binding/digest helpers.
- `tests/test_playlist_improvement.py` — token, candidate, validator, and binding tests.

Modified:

- `src/xfinaudio/headless/playlist_editor.py` — session-scoped token map, proposal
  binding, and the dedicated proposal-bound save command; manual behavior unchanged.
- `tests/test_headless_playlist_editor.py` — editor authorization and exact-order save
  tests.

### Landed in I2 (AI boundary, mocked provider)

Committed as `38dbcc6`, `6733dff`, and `235caae`.

Modified:

- `src/xfinaudio/ai/structured_assists.py` — the strict token-only
  `ImprovementInterpretation` model and `interpret_improvement_request`; the legacy
  `EditorInterpretation` offline path is retained.
- `src/xfinaudio/ai/structured_common.py` — editor-specific improvement composition
  that does not widen the shared `_POLICY` or the 4096-character response bound.
- `src/xfinaudio/headless/ai_context.py` — the exact `editId`/`draftIds`/
  `includeReplacements` improvement selector, the bounded candidate set, the per-request
  disclosure, and the draft-order fingerprint.
- `src/xfinaudio/headless/ai_execution.py` — improvement execution and the local
  before/after preview path carrying `proposalId`/`digest`.
- `src/xfinaudio/headless/optional_ai.py` — one-shot consent retained through
  `ai.apply`, with random tokens kept out of `revision_data`.

Tests landed in `tests/test_ai_structured_assists.py`, `tests/test_ai_request_privacy.py`,
`tests/test_headless_ai_context.py`, and `tests/test_headless_optional_ai.py`. The
planned `tests/test_headless_playlist_improvement.py` and
`tests/test_headless_ai_improvement.py` were never created; I1/I2 focused verification
ran against the improvement, editor, context, and optional-AI targets that exist.

### Landed in I3 (Electron renderer and security)

Committed as `f60f81b`, `7aef8b9`, `a8ccb5a`, `a74bbed`, and `e9bccb9`.

Modified:

- `desktop-electron/src/main.ts`, `desktop-electron/src/preload.ts`, and
  `desktop-electron/src/security.ts` — the `savePlaylistImprovement` route, its
  `{editId, name, proposalId, digest, draftIds}` fields, and the bounded improvement
  context (`draftIds`, `includeReplacements`) with the 2..80 draft bound and digest
  validation.
- `desktop-electron/renderer/editor.ts` — the bounded `ImprovementPreview` parser,
  `setImprovementPreview`, `applyImprovementPreview`, the draft-to-proposal binding, and
  the dedicated `savePlaylistImprovement` call; the legacy manual preview/save path is
  unchanged.
- `desktop-electron/renderer/app.ts` — the improvement selector published through
  `syncAiContext`, the CTA availability derived from the exact draft and from the
  presence of the save bridge, and the local-preview apply branch.
- `desktop-electron/renderer/editor-view.ts` — the "Mejorar con IA…" CTA and the numbered
  ANTES/DESPUÉS lists with readiness, score, warnings, and explicit apply/keep-separate
  copy.
- `desktop-electron/renderer/optional-ai.ts` and
  `desktop-electron/renderer/optional-ai-view.ts` — the default-off "Incluir reemplazos"
  toggle, the improvement disclosure, and the 2000-character improvement prompt.

Tests landed in `desktop-electron/tests/renderer.editor.test.mjs`,
`renderer.editor-view.test.mjs`, `renderer.optional-ai-app.test.mjs`,
`optional-ai.test.mjs`, `optional-ai-view.test.mjs`, `optional-ai-host.test.mjs`,
`editor-security.test.mjs`, and `workflow.integration.test.mjs`.

## Safety and security

- No audio or Serato write touches this feature; the only persistence is the existing
  `compare_and_update` save, reached through the proposal-bound command.
- `AppState` is not involved; the draft is renderer-local and the backend session is
  request-scoped.
- Provider output is untrusted text and untrusted tokens; it is never rendered as HTML
  and never used to resolve a path directly.
- Tokens are ephemeral and local-only; no path or `sha256(path)` id reaches the
  provider.
- No dependency, no network in tests, no credential inspection.

## Resolved caveats (previously "unresolved technical caveats")

The first revision listed five open caveats. The challenge and the bounded design above
resolve them as follows; they are no longer open and are not a reason to block I1:

1. **Replacement-pool composition.** Fixed at up to 20 deterministic, disclosed,
   complete-metadata candidates; the pool is opt-in per request and empty when
   disabled. Incomplete-metadata candidates are excluded at selection time and that
   exclusion is disclosed.
2. **Locked versus replaced tracks.** The saved editor has no locks or excludes, so no
   such rule is asserted. `validate_edit`'s optional lock/exclude parameters remain for
   other callers and are not used here.
3. **Metadata completeness.** Incomplete pool candidates are excluded before the
   proposal is built, so `assess_playlist_edit` cannot fail a whole proposal because of
   a pool candidate's missing BPM/energy/key.
4. **Durable spec reconciliation.** Recorded as
   `openspec/specs/electron-playlist-improvement/spec.md` (I4.3); the manual rejection
   wording is not weakened and `my-playlists-screen/spec.md` is untouched.
5. **Canonical instruction bound.** Fixed at 2000 characters for the AI improvement
   prompt across renderer, bridge, and backend; the legacy manual request is 500 only at
   the renderer input/UI, while its pre-existing IPC/backend bound is 2000 (see
   "Canonical instruction bound (as built)").

## Review slices

Every slice is one or more reviewable work units under the 400-line review heuristic,
committed conventionally without AI attribution. The chain is ordered: I1 before I2
before I3; I4 verifies the integrated result. Split further before exceeding the budget.

As built, I1 became five dependency-complete work-unit commits (`56c491c` → `75a11a2` →
`7dadafb` → `1297e12` → `4707dbd`), each carrying its tests, with the final tree
identical to the preserved original `97370f5`. I2 landed as `38dbcc6`, `6733dff`, and
`235caae`; I3 landed as `f60f81b`, `7aef8b9`, `a8ccb5a`, `a74bbed`, and `e9bccb9`, with
ODD-task documentation closure `4533422`. Two units exceed the advisory 400-line review
heuristic and are disclosed rather than minimized: `75a11a2` at 461 changed lines and
`235caae` at 446 changed lines; each keeps its logic and tests coherent. The independent
offline gate and commit evidence is recorded once in `verify-report.md`, all with mocked
transports. Acknowledged native receipts exist only for the documentation chain
`4533422..88ab13a`, I3 U1 `f60f81b`, and I3 U2 `7aef8b9`; the `7aef8b9..a74bbed` slice
stopped unapproved at lineage `review-c5bd20ee943fbd91`
(`native_stop_required`/`unknown_causality`), and the I1, I2, first-docs `7d381ae`, and
U4b `e9bccb9` slices have no receipt. Clone-local RDD is off by explicit user choice; that
waives the pending native review but is never feature-level or delivery approval. No live
provider or real library was reached, and visual macOS behavior was not observed.
The durable `openspec/specs` reconciliation landed as
`openspec/specs/electron-playlist-improvement/spec.md` (I4.3), which records the as-built
behavior and marks live provider, native-dialog, visual macOS, and real-library
acceptance as pending; any such validation remains pending.
