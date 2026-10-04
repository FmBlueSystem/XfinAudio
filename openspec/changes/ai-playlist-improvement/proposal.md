# AI-guided concrete playlist improvement

## Intent and problem

A DJ who already owns a saved playlist wants to tell optional AI how to improve it and
then inspect concrete track substitutions and a concrete order before anything local
changes. The existing optional-AI editor surface cannot satisfy this: it interprets a
request into one of four offline operations (`shorten_tracks`, `shorten_minutes`,
`rising_energy`, `falling_energy`) and hands the text back to the deterministic local
parser, so the model never proposes concrete track identities. The Editor therefore
cannot answer "replace these two and open with that one".

This change introduces a bounded, consent-first, token-only path in which the model may
propose a concrete ordered selection from a locally authorized candidate set, and the
app validates, previews, and applies it to the local draft only.

## Correction notice (2026-10-04, documentation revision)

The first authored revision of these artifacts was based on assumptions an independent
read-only challenge disproved against the current source. This revision replaces those
assumptions with the safe design they force. The disproved assumptions were:

1. **"Widening `EditSession.paths_by_id` with replacement ids is enough to save a
   replacement."** Disproved. `PlaylistEditor.execute` routes `playlist.edit.save`
   through `_paths`, which calls `validate_edit(session.original.track_paths, paths)`.
   `validate_edit` rejects any candidate multiset that exceeds the source multiset
   ("A draft cannot add unknown or duplicate tracks"), independent of `paths_by_id`, and
   `_paths` additionally requires every id to be exactly 64 characters. A replacement
   save needs an explicit, proposal-bound authorization, not a wider lookup table.
2. **"The renderer can add replacement tracks to the draft and save them."** Disproved.
   `SavedPlaylistEditor.updateTracks` replaces the draft array wholesale and holds no
   authorization state; a draft containing a new id is rejected at `savePlaylistEdit`
   by the backend `_paths`/`validate_edit` path. The renderer cannot authorize adding.
3. **"`sha256(path)` ids are anonymous."** Disproved. `_public_track` derives each id as
   `sha256(track.path)`. It is deterministic and verifiable offline by anyone holding
   the id, and correlatable across requests and surfaces. It is a pseudonym, not a
   confidentiality boundary.
4. **"64-hex ids can express a full ordered proposal."** Disproved. `strict_object`
   bounds a provider response to 4096 characters. A 64-hex id plus JSON punctuation is
   about 67 characters per element, so a full order fails above roughly 55 tracks. The
   previous design's 500-id response bound was unreachable.
5. **"The saved editor inherits locked/excluded constraints."** Disproved.
   `PlaylistEditor._paths` calls `validate_edit(...)` with no `locked_paths` or
   `excluded_paths`; the saved-editor surface has no lock or exclude controls at all.
   No locked/excluded behavior exists there to preserve, and the AI path must not
   assert it.
6. **"Editor AI context reflects the current unsaved draft."** Disproved.
   `build_context(surface="editor")` fingerprints only `[session.edit_id,
   session.revision]` plus library records. The renderer's unsaved draft order is
   absent, so a proposal could be prepared against a draft the user had since changed.

## Approved scope (in)

- A free-text improvement instruction on an already-open saved-playlist editor draft.
- A per-request disclosure preview that names the exact bounded metadata, the exact
  candidate counts, the exact provider tokens, and the transmission meaning, before any
  authorization. Tokenization is disclosed as pseudonymization, not anonymity.
- An explicit, per-request consent step (native confirmation) with no implicit reuse.
- A strictly validated, token-only model response: every token must resolve inside the
  request-scoped authorized candidate set.
- A local before/after ordered diff with the existing musical assessment.
- Apply to the editor draft only, then a **dedicated, proposal-bound exact-order save
  authorization** that can persist the one validated replacement order. Saving stays a
  separate, explicit action.
- The offline deterministic editor path keeps working with AI disabled or unconfigured.

## Out of scope (explicitly)

- Any real provider, credential, network, or telemetry call. Tests use mocked or
  injected transports only.
- Any real-library scan or use of the running combined preview, main checkout,
  installed app, or existing app/library data.
- Any audio mutation, Serato database write, export, or DSP change.
- Any path disclosure: the provider never receives filesystem paths, raw metadata
  dumps, raw audio, or `sha256(path)` identifiers.
- A general "add any library track to a playlist" feature. Replacement candidates exist
  only inside a bounded, disclosed, request-scoped pool.
- Automatic request, automatic apply, or automatic save.
- Widening the shared 4096-byte provider-response bound, the shared `_POLICY`, the
  shared 64 KiB request bound, or the global default model for other surfaces.
- New dependencies, coverage-floor changes, push, PR, merge, or app replacement.
- Re-auditing or rewriting the existing offline parser and assessment engine.

## Chosen direction (user decisions already made, refined by the challenge)

1. The user chose **concrete track/ordering proposals** over translating requests into
   the four existing limited operations.
2. The user authorized local implementation on an isolated `feat/ai-playlist-improvement`
   branch rooted at the clean `fix/prep-ai-readiness` commit `ba58326`.
3. Each real request stays **opt-in per request**, with a precise payload preview and a
   native confirmation; local preview and explicit save stay separate.
4. Replacement support is preserved, but only through a narrow chain: ephemeral
   request-scoped tokens, a bounded candidate pool, a local exact-order validator, and a
   dedicated proposal-bound save command that the manual path does not share.

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Model selects a track the user never authorized | Local allow-list of ephemeral tokens; every returned token must resolve inside the request-scoped candidate set, otherwise no edit. |
| Deterministic ids leak path guesses or correlate requests | Provider sees only freshly generated random 16-hex tokens, unique per request, mapped only in local memory, never persisted, never reused. |
| Model or transport echoes a path, secret, or audio | `redact_paths` on the instruction, token-only response schema, bounded candidate fields, no path or audio in the payload. |
| Ordered proposal cannot fit the response budget | Compact 16-hex tokens plus explicit caps (`<=80` draft, `<=20` replacement, `<=100` total) keep the worst-case order near 2,340 bytes, inside the unchanged 4096-byte bound. |
| Huge playlist silently truncated | The improvement context fails closed with a clear message above 80 draft tracks; no silent truncation, draft untouched. |
| Stale response applied to a changed draft or playlist | `edit_id`, saved `_revision`, candidate-set digest, and the current renderer draft-order fingerprint are re-validated at prepare, after receive, and before preview/apply/save. |
| Replacement save silently relaxes the manual no-new-path invariant | The manual `playlist.edit.save` path is unchanged; a separate proposal-bound command can persist only the one exact, previously validated order, and only while the draft still matches that proposal. |
| A manual edit after applying a preview slips additions past the manual save | Applying a preview binds the draft to the proposal; any later manual mutation invalidates the binding, disables the improvement save, and requires re-running the proposal or discarding. Fail closed. |
| Claiming inherited locks that do not exist | Saved-editor locks/excludes are documented as absent; the AI validator enforces only membership, uniqueness, bounds, and exact-order binding. |
| Model output treated as instructions or executable | Output is coerced into a strict Pydantic/`strict_object` schema; unknown fields, duplicates, non-objects, oversized values, non-token ids, and `NaN`/`Infinity` are rejected. |
| Global model/policy widening to fit a new schema | The improvement schema and any per-request model choice are editor-specific; `_POLICY`, `strict_object`, `provider_request`, and the default model are not globally changed. |
| Accidental live traffic during development | Runner boundary: no provider, credential, network, or real-library access; mocked transports and synthetic fixtures only. |
| Review slices exceeding the 400-line budget | Feature-branch chain with work-unit commits and explicit per-slice splitting. |

## Rollback plan

Revert the ordered feature-branch commits for this change. No database migration, no
settings migration, no audio or Serato write, and no new dependency is introduced, so a
revert returns the editor to the current offline-only proposal behavior. Draft state is
in-memory in the renderer and is discarded on revert.

## Success criteria

- From the saved-playlist editor, a user can type an instruction and see the exact
  bounded metadata, candidate counts, and provider tokens that would be disclosed,
  before consent, including the explicit statement that tokens are pseudonyms and that
  titles/artists are transmitted.
- No title, artist, path, `sha256(path)` id, or credential leaves the app without that
  request-specific authorization, and never any filesystem path or raw audio.
- A bounded response that references only authorized tokens yields a local before/after
  diff and assessment; malformed, stale, unknown, duplicate, out-of-scope, or
  over-budget responses produce no edit and a clear message.
- Applying the preview changes only the draft; saving the replacement order uses the
  dedicated proposal-bound save; nothing happens automatically.
- Existing offline editing, the manual no-new-path rejection, no-audio-mutation, and the
  atomic compare-and-update save remain intact. The editor is not described as having
  locks or excludes it does not have.
- The shared response bound, shared policy, shared request bound, and global default
  model are not widened; the improvement path is editor-specific.
- Strict TDD is observed (RED → GREEN → REFACTOR) for every behavior slice, with
  focused Python and Node tests plus the repository gates, and never an overridden
  coverage floor.

## Chained review plan (feature-branch chain; each slice <= 400 changed lines)

1. **I1 — Bound concrete local edit proposals (Python editor).** Ephemeral token
   generation, authorized candidate set, id-only proposal schema, dedicated
   `validate_improvement_proposal`, proposal binding, draft-only preview, and
   stale/CAS rejection. Tests first.
2. **I2 — Bound AI proposal and disclosure (AI boundary).** Strict provider response
   schema, bounded token/metadata disclosure, per-request confirmation, draft-order
   freshness, and the editor-specific schema policy; mocked provider only. Tests first.
3. **I3 — Connect editor instruction to local review (Electron renderer).** Explicit
   instruction → disclosure → response → readable diff and local preview → draft apply
   → proposal-bound save; separate manual save; no automatic network. Tests first.
4. **I4 — Verify integrated feature and document handoff.** Offline Python/Node gates
   and structural checks by a delegated verifier; reconcile artifacts with observed
   implementation; record remaining limits. No live/provider/visual claim from mocks.

Each slice is committed as one or more reviewable work units that keep code and tests
together; documentation reconciliation happens in I4.2. Split a slice further before its
diff exceeds the budget. Conventional commits only, no AI attribution, and no push, PR,
merge, release, or deployment.

**As-built note (I1).** I1 landed as five dependency-complete work-unit commits, each
carrying its tests: `56c491c` (tokens, 155 lines), `75a11a2` (bounded candidates, 461
lines), `7dadafb` (validation/binding, 396 lines), `1297e12` (editor authorization, 165
lines), and `4707dbd` (exact-order CAS save, 285 lines). The final tree is byte-identical
to the preserved original `97370f5`. The 461-line candidate-set unit is an explicit
advisory overage of the 400-line heuristic, disclosed rather than minimized. I1 was
backend-only; I2, I3, and I4 are not implemented, and no push, PR, merge, provider,
credential, network, or real-library access was performed.
