# Apply progress

## 2026-10-04 — Challenge correction of OpenSpec artifacts (documentation only)

An independent read-only challenge disproved six assumptions in the first authored
revision of these artifacts against the current source. This session corrects
`proposal.md`, `spec.md`, `design.md`, `tasks.md`, this file, `verify-report.md`, and
`state.yaml` so the plan preserves genuine replacement support safely instead of
dropping it or widening the manual path.

Disproved assumptions and the correction each forced:

1. **Widening `EditSession.paths_by_id` would let `playlist.edit.save` accept
   replacements.** False: `_paths` calls `validate_edit(session.original.track_paths,
   paths)`, which rejects any addition, and requires 64-character ids. Correction: a
   dedicated `ImprovementProposal` binding plus a separate proposal-bound exact-order
   save command; the manual command is untouched.
2. **The renderer can add replacements.** False: `SavedPlaylistEditor.updateTracks`
   only replaces the array and holds no authorization; the backend save rejects the
   addition. Correction: the backend authorizes and persists the one validated order;
   the renderer never sends a raw path list on the improvement save.
3. **`sha256(path)` ids are anonymous.** False: `_public_track` derives them
   deterministically from the path, so they are offline-verifiable and correlatable.
   Correction: fresh `16`-hex ephemeral provider tokens per request, mapped only in
   local memory, never persisted or reused; disclosure states pseudonymization, not
   anonymity.
4. **A 64-hex full order fits the response bound.** False: the shared `strict_object`
   bound is 4096 characters and 64-hex ids plus punctuation fail above about 55 tracks.
   Correction: compact tokens plus caps of `<=80` draft, `<=20` replacement, `<=100`
   total, keeping the worst case near 2,340 characters inside the unchanged bound; the
   shared bound is not widened.
5. **The saved editor inherits locked/excluded constraints.** False:
   `PlaylistEditor._paths` passes no `locked_paths`/`excluded_paths`, and the saved
   editor has no lock/exclude controls. Correction: requirements and design no longer
   assert locks/excludes; the AI validator enforces membership, uniqueness, bounds, and
   exact-order binding only.
6. **Editor AI context reflects the current unsaved draft.** False:
   `build_context(surface="editor")` fingerprints only `[session.edit_id,
   session.revision]` plus library records. Correction: the ordered renderer draft ids
   enter the editor selector and the context revision, so a draft change invalidates
   prepare/receive/apply.

Additional corrections carried through the artifacts:

- Conservative explicit limits are stated (`MAX_DRAFT_TRACKS = 80`,
  `MAX_REPLACEMENT_CANDIDATES = 20`, `MIN_IMPROVEMENT_TRACKS = 2`,
  `MAX_IMPROVEMENT_PAYLOAD_BYTES = 32 * 1024`) with fail-closed behavior above the
  draft cap and no silent truncation.
- The canonical instruction bound is fixed at 2000 characters, with I3 aligning the
  renderer input and view.
- The improvement schema, token format, caps, and any per-request model choice are
  editor-specific; the shared `_POLICY`, the 4096-character response bound, the 64 KiB
  request bound, and the global default model are not widened.
- Consent remains one-shot and per request; `ai.run` still requires `confirmed is True`
  and the native `OptionalAiHost.ask()` confirmation; there is no auto-send.

What this session did:

- Read `odd/tasks/ai-playlist-improvement.md`, the seven artifacts, `openspec/config.yaml`,
  the project `AGENTS.md`, and the relevant source: `playlist_edit_intents.py`,
  `playlist_editor.py`, `common.py`, `ai_context.py`, `ai_execution.py`,
  `optional_ai.py`, `structured_common.py`, `structured_assists.py`, `ai_transport.py`,
  `security.ts`, `editor.ts`, `optional-ai.ts`, and `app.ts`.
- Rewrote the seven artifacts to match the corrected design.

What this session did **not** do:

- No source or test change of any kind. Only the seven allowed artifacts were written.
- No test written or run, so there is **no RED and no GREEN evidence**.
  `strict_tdd: true` applies to the later behavior changes (I1–I3), not to this
  documentation correction.
- No provider, credential, network, or real-library access. No fixture was executed.
- No `release_gate_check.py --run` and no `npm test`; no coverage claim.
- No commit, stage, push, PR, or merge.
- `odd/tasks/ai-playlist-improvement.md` was read but not edited.

## 2026-10-04 — Initial OpenSpec artifacts (pre-implementation, superseded)

The first session produced repository-required OpenSpec documentation before any source
write. It read the ODD task, `openspec/config.yaml`, the project `AGENTS.md`/SDD skill,
and the conventions in `openspec/changes/*` (notably `conversational-library-create`,
`ai-review-live-local`, `electron-playlist-editor`, `optional-structured-ai`,
`replacement-controls`), and inspected the existing editor, AI boundary, and Electron
surfaces. It authored the seven artifacts and recorded reuse of `OptionalAI` +
`OptionalAiHost`, the id-only contract, the invariant split, and preview-then-apply-then-
save. Its inaccurate assumptions are listed and corrected above.

## Decisions recorded from both sessions

1. **Route.** Direct ODD documentation with strict TDD for the behavior slices. Status
   and phases in `state.yaml` reflect docs-complete, I1 landed, and apply in progress;
   I2–I4 are pending.
2. **Reuse, don't duplicate.** `OptionalAI` + `OptionalAiHost` own consent and native
   confirmation; no second consent path is introduced. A new save command is added only
   because exact-order replacement persistence genuinely needs one.
3. **Token-only contract.** The provider returns only ephemeral 16-hex tokens from a
   locally authorized candidate set plus an optional bounded rationale; the server
   resolves tokens to paths locally.
4. **Invariant split, narrowly.** The manual no-new-path invariant is unchanged; the AI
   path gets ephemeral tokens, a separate validator, and a proposal-bound exact-order
   save. Locks/excludes are not asserted.
5. **Preview, then apply, then bound save.** The AI result becomes a local before/after
   diff and assessment; applying binds the draft to the proposal; saving routes to the
   proposal-bound command; any manual mutation invalidates the binding.
6. **Review chain.** I1 (tokens/candidate/validator/proposal) → I2 (AI
   schema/disclosure/freshness) → I3 (Electron review and save routing) → I4 (verify).

## 2026-10-04 — I1 local proposal and exact-order save

I1 was originally completed in commit `97370f50d360bdd993d805c3166106775d801001` (later re-partitioned as recorded below):
request-scoped random tokens, bounded draft/replacement candidates, token-only
validation, a session-bound proposal, and an explicit exact-order replacement save
that retains CAS. The ordinary manual save continues to reject additions. Tests
preceded production code: observed RED from the missing module and method, then
GREEN with 136 focused tests and negative/collision/stale cases. Independent gate
initially failed on 32 new-test Pyright errors and then on 2 source-format checks;
both were corrected, and the complete offline gate reran successfully: 4,293
Python passed, 94.45% coverage, 0 Pyright errors, Ruff lint/format, release smoke,
source docs/hygiene, packaging check and PyInstaller check-only all passed. No Node
suite, real provider, credentials, library scan, or live UI was exercised for I1.

The original I1 commit contained 1,459 additions and 1 deletion. After the user's
explicit authorization, only that local commit was reworked into five dependent
work-unit commits: `56c491c` (tokens, 155 lines), `75a11a2` (candidate set, 461 lines),
`7dadafb` (validator/binding, 396 lines), `1297e12` (editor authorization, 165 lines),
and `4707dbd` (exact-order CAS save, 285 lines). Each commit includes its tests and
passed its focused suite (57/87/113/119/136 respectively); an independent targeted
rerun on the final tree observed 124 focused tests. Final tree matches the backup
`97370f5` exactly. The 461-line candidate-set unit exceeds the advisory 400
because its selection behavior and tests must stay together. The original commit
remains reachable under `backup/ai-playlist-improvement-97370f5`.

Committed-range native ASSESS was unassessable while these OpenSpec/ODD paths were
untracked. INSPECT with those paths excluded returned
`empty_candidate_base_ref_required` for an empty workspace projection, not an
executable START. These results predate the five rewritten commit identities; no
fresh native review approval or receipt is claimed. Independent functional
verification does not imply one.

## 2026-10-04 — Artifact reconciliation before Git add

I1 has landed, so this pass reconciled the untracked ODD task and all seven artifacts
with the observed code and gate evidence before they were added to Git. Corrections:

- `tasks.md` no longer says no task is done, records the five landed I1 commits, and no
  longer over-claims that `_fresh()` can observe client-only draft edits.
- `design.md` splits its affected files into landed-I1 and planned-I2/I3 sets and
  records the as-built review slices.
- `verify-report.md` is explicitly **partial**: I1 independently verified, I2–I4
  pending, no native review approval claimed.
- `spec.md` R12 is scoped to the draft snapshot the client actually submits.
- `state.yaml` keeps `apply: in-progress` and `verify: pending`.

Structural whitespace and YAML checks were rerun after the edits. No source, test,
provider, network, or credential work was performed, and nothing was staged or
committed.

## Next step

Resolve the native review/workload boundary without inventing a START route, then
implement I2's editor-specific AI response/disclosure with mocked transports. I3
renderer wiring and I4 end-to-end checks remain pending. Existing documentation
claims of no source change above describe only the earlier documentation sessions.
