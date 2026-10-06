# Tasks

Status legend: `[ ]` not started, `[x]` done. Slices I1, I2, and I3 are implemented and
their tasks are checked; slice I4 artifact reconciliation, durable-spec reconciliation,
and limits are recorded, with any live provider/visual/library acceptance still pending.
This file was authored (and corrected after the read-only challenge) before
implementation and is kept as the plan plus as-built record for slices I1–I4.

Repository source of truth: `AGENTS.md` (strict TDD, no audio mutation, no DSP, no live
Serato V2 writes, immutable `AppState`, pinned dependencies, 400-line review budget).

Correction note: the first revision of this plan assumed that widening
`EditSession.paths_by_id` would let `playlist.edit.save` persist replacements, that the
renderer could add replacements to a draft and save them, that `sha256(path)` ids were
anonymous, that a 64-hex full order fit the response bound, that the saved editor had
locks/excludes, and that the editor AI context included the unsaved draft. All six were
disproved against source. The tasks below implement the safe replacements: ephemeral
tokens, conservative caps, a draft-order fingerprint, and a dedicated proposal-bound
exact-order save that leaves the manual path intact.

As-built status: I1 landed as five dependency-complete work-unit commits `56c491c`
(tokens, 155 lines) → `75a11a2` (bounded candidates, 461 lines) → `7dadafb`
(validation/binding, 396 lines) → `1297e12` (editor authorization, 165 lines) →
`4707dbd` (exact-order CAS save, 285 lines), each carrying its tests. The final tree is
identical to the preserved original `97370f5` (`backup/ai-playlist-improvement-97370f5`).
I2 landed as `38dbcc6`, `6733dff`, and `235caae`; I3 landed as `f60f81b`, `7aef8b9`,
`a8ccb5a`, `a74bbed`, and `e9bccb9`, with ODD-task documentation closure `4533422`. Two
units exceed the advisory 400-line review heuristic, disclosed rather than minimized:
`75a11a2` at 461 changed lines and `235caae` at 446 changed lines (422 additions, 24
deletions). The independent offline gate and commit evidence is recorded once in
`verify-report.md`. Acknowledged native receipts exist only for the documentation chain
`4533422..88ab13a` (`review-c9c388e5ff8775f0`), I3 U1 `f60f81b`
(`review-3eca483813fe5bd4`), and I3 U2 `7aef8b9` (`review-f141608a936191bd`); the
`7aef8b9..a74bbed` slice (U3 `a8ccb5a` and U4a `a74bbed`) stopped unapproved at lineage
`review-c5bd20ee943fbd91` with `native_stop_required`/`unknown_causality`, and the I1, I2,
first-docs `7d381ae`, and U4b `e9bccb9` slices have no receipt. Clone-local RDD is off by
explicit user choice; that waives the pending native review but is never feature-level or
delivery approval. No push, PR, merge, provider, credential, network, or
real-library access was performed, and no visual macOS behavior was observed.

## Contract decisions already frozen (I1.0 is closed)

- **Manual invariant unchanged.** `playlist.edit.save`, `_paths`, and `validate_edit`
  keep rejecting additions. No map widening.
- **Token format.** Ephemeral `16`-hex tokens (`secrets.token_hex(8)`), unique per
  request, mapped only in local memory, never persisted or reused.
- **Caps.** `MAX_DRAFT_TRACKS = 80`, `MAX_REPLACEMENT_CANDIDATES = 20`,
  `MAX_CANDIDATES = 100`, `MIN_IMPROVEMENT_TRACKS = 2`; fail closed above the draft cap
  with no silent truncation.
- **Payload/response budgets.** `MAX_IMPROVEMENT_PAYLOAD_BYTES = 32 * 1024`; the shared
  `strict_object` 4096-character response bound is unchanged, and the compact tokens
  keep the worst-case order near 2,340 characters.
- **Freshness.** The current renderer draft order enters the editor context and its
  fingerprint; the draft is bound to `proposal_id` + `digest` on apply.
- **Locks/excludes.** Not asserted on the saved-editor surface; the AI validator
  enforces membership, uniqueness, bounds, and exact-order binding only.
- **Instruction bound.** AI improvement prompt fixed at 2000 characters across the
  renderer, the IPC bridge, and the backend. The earlier frozen plan to raise the legacy
  manual renderer input to 2000 was **not** implemented: the legacy manual UI stays at
  500, while the IPC bridge (`security.ts` `previewPlaylistEdit`) and the headless
  backend (`playlist_editor.py` `playlist.edit.preview`) already accepted 2000 before
  this change and were not touched. There is no end-to-end manual 500 bound, and the
  manual command does not universally reject instructions above 500.
- **Model policy.** Editor-specific improvement schema; `_POLICY`, the shared response
  bound, `MAX_REQUEST_BYTES`, and the default model are not globally widened.

## Slice I1 — Bound concrete local edit proposals (Python editor)

1. [x] **I1.0 — Freeze the candidate and save contract.** Resolved above and in
   `design.md`; no open caveat blocks coding.
2. [x] **I1.1 — RED: ephemeral tokens are random, unique, and local-only.** Failing
   tests that each authorized candidate receives a fresh 16-hex token, that tokens are
   unique within a request, that two requests with the same draft produce different
   tokens, and that the same path never yields a stable cross-request token. Observe
   the failure before any production change.
3. [x] **I1.2 — GREEN: pure token + candidate module.** Implement
   `src/xfinaudio/application/playlist_improvement.py` with token generation, the
   bounded draft+pool candidate selection, and the token→path mapping. No transport,
   no renderer, no persistence.
4. [x] **I1.3 — RED: candidate set is locally built and bounded.** Failing tests that
   the authorized set contains the open draft's tokens in draft order, that when
   replacement is enabled the pool is `<=20` and excludes draft paths, excluded paths,
   and incomplete-metadata candidates, and that a draft above 80 fails closed without
   truncation.
5. [x] **I1.4 — GREEN: bounded selection.** Implement the selection and mapping needed
   to pass I1.3, including the fixed caps and the fail-closed path.
6. [x] **I1.5 — RED: token-only validator rejects unsafe proposals.** Failing tests for
   unknown tokens, duplicates, out-of-scope tokens, 64-hex ids, empty lists, oversized
   lists, additions beyond the pool cap, and a below-minimum resulting count.
7. [x] **I1.6 — GREEN: `validate_improvement_proposal`.** Implement the dedicated
   validator and token→path resolution. Keep `validate_edit` and `PlaylistEditor._paths`
   exactly as they are; prove it with an explicit regression test that the manual path
   still rejects additions.
8. [x] **I1.7 — RED: proposal binding and dedicated exact-order save.** Failing tests
   that a manual `playlist.edit.save` of a replacement draft still fails, that the
   dedicated proposal-bound save persists exactly the validated order, and that a
   mismatched `proposal_id`, digest, edit session, saved revision, or current draft
   order fails closed with no write.
9. [x] **I1.8 — GREEN: session-scoped proposal.** Extend `PlaylistEditor` (or a
   narrowly scoped collaborator) so the validated order is stored as an
   `ImprovementProposal`, resolved only through the session token map, re-checks
   freshness before and after, and is the only route by which an addition can be saved.
10. [x] **I1.9 — REFACTOR + TRIANGULATE.** Remove duplication, name the bounds as
    constants, and exercise negative/alternate cases that materially protect the
    contract (token collision regeneration, draft/pool path collision, repeated token,
    100/101 and 80/81 boundaries, manual edit after apply invalidating the binding).
11. [x] **I1.10 — VERIFY focused.** `uv run pytest -q
    tests/test_playlist_improvement.py tests/test_headless_playlist_editor.py
    tests/test_playlist_edit_intents.py tests/test_playlist_edit_assessment.py
    tests/test_playlist_editor_drafts.py`
    and focused `uv run pyright` / `uv run ruff check` on touched files. As built, the
    planned `tests/test_headless_playlist_improvement.py` was never created; the I1
    focused verification ran against the existing improvement/editor targets
    (57/87/113/119/136 tests per commit). I1 was then reworked into the five work-unit
    commits listed at the top of this file, each carrying its tests; no docs were part
    of I1 (documentation reconciliation is I4.2).

## Slice I2 — Bound AI proposal and disclosure (AI boundary, mocked provider)

As built: landed as three work units `38dbcc6` (strict token response + policy), `6733dff`
(bounded disclosure + draft-order freshness), and `235caae` (consented proposal binding +
local preview). The `235caae` unit is 446 changed lines (422 additions, 24 deletions), an
explicit advisory overage of the 400-line heuristic. All transports were injected or
mocked; no credential or network access occurred.

12. [x] **I2.0 — RED: strict token improvement response schema.** Failing tests for a
    non-object, extra key, duplicate key, over-4096 payload, `NaN`/`Infinity`, non-list
    `orderedTrackIds`, a 64-hex id, a non-16-hex token, duplicate token, empty list,
    oversized list, a control-character `rationale`, and a `rationale` over 400
    characters.
13. [x] **I2.1 — GREEN: strict model + token payload.** Add the strict model and
    `interpret_improvement_request` in `structured_assists.py`, composed with an
    editor-specific schema string, and wire `ask_object` with the token/metadata
    payload. Assert a captured payload contains no path, no `sha256(path)` id, no raw
    audio, no unauthorized corpus, and stays within the payload budget.
14. [x] **I2.2 — RED: exact, per-request disclosure and draft freshness.** Failing
    tests that `build_context(surface="editor")` discloses the candidate counts, the
    exact field list, token semantics, and the replacement on/off decision; that the
    disclosure and context revision change when the candidate set or the submitted
    draft order changes; that a draft above the cap fails closed; and that `_fresh()`
    compares the submitted draft snapshot, since it cannot observe a client-only edit
    the renderer never reports.
15. [x] **I2.3 — GREEN: disclosure, draft fingerprint, and consent in `OptionalAI`.**
    Extend the `editor` surface so `ai.prepare` returns the exact disclosure,
    `ai.confirmation` re-checks freshness against the frozen stable selector and the
    submitted draft snapshot, `ai.run` requires `confirmed is True`, and `ai.apply`
    returns the local preview data plus `proposalId`/`digest`. Keep one prepare-time
    candidate/token snapshot stable through run/apply and never place random tokens in
    `revision_data`; the renderer invalidates its pending preview on every local draft
    mutation. Reuse `_fresh`/`_pending`/`invalidate`; do not add a second consent
    mechanism.
16. [x] **I2.4 — RED/GREEN: untrusted response cannot produce an edit.** Failing tests
    that an unauthorized token, a path string, a 64-hex id, or a stale reference
    reaches no edit and raises the existing safe error codes without echoing raw
    provider text.
17. [x] **I2.5 — RED/GREEN: editor-specific policy is not globally widened.** Failing
    tests that other surfaces keep `_POLICY`, the 4096-character response bound,
    `MAX_REQUEST_BYTES`, and the default model unchanged, while the editor improvement
    call uses its own schema and token bounds.
18. [x] **I2.6 — VERIFY focused.** `uv run pytest -q tests/test_headless_ai_context.py
    tests/test_headless_optional_ai.py tests/test_headless_ai_execution.py
    tests/test_ai_structured_assists.py tests/test_ai_request_privacy.py
    tests/test_headless_playlist_improvement.py` plus focused type/lint checks. As
    built, neither `tests/test_headless_ai_execution.py` nor
    `tests/test_headless_playlist_improvement.py` was created; focused verification ran
    against the existing improvement, editor, context, and optional-AI targets, and I2
    landed as three work units rather than one. All transports injected; no credential,
    no network.

## Slice I3 — Connect editor instruction to local review (Electron)

As built: landed as five work units `f60f81b` (save bridge + bounded selector),
`7aef8b9` (proposal-bound preview), `a8ccb5a` (disclosure), `a74bbed` (draft-preview
wiring), and `e9bccb9` (before/after preview UI), with ODD-task documentation closure
`4533422`. Independent full offline Node: 480 passed, 0 skipped. The AI improvement
prompt is bounded at 2000 characters end to end; the legacy manual renderer input keeps
its 500-character bound, while the pre-existing IPC/backend manual preview bound is
2000, so the earlier plan to align `editor.ts` to 2000 was not implemented and the
manual path was not narrowed to an end-to-end 500 bound.

19. [x] **I3.0 — RED: readable local diff and preview.** Failing Node tests that a
    validated editor improvement result renders a before/after ordered diff with the
    assessment, that `editor.preview` is set with its `proposalId`/`digest` binding,
    and that the draft and saved playlist are unchanged until the user acts.
20. [x] **I3.1 — GREEN: `showImprovement` + diff view.** Extend `SavedPlaylistEditor`
    and `editor-view.ts`. Keep the existing generation guard, `invalidatePreview`, and
    `applyPreview`/`save` controls; Spanish UI copy consistent with current strings.
21. [x] **I3.2 — RED: apply is draft-only and save stays explicit.** Failing tests that
    "Aplicar al borrador" mutates only the draft and binds it to the proposal, that
    saving routes to the proposal-bound command while the binding is valid, that a
    manual mutation after apply disables that save, and that no save/apply/network
    occurs during prepare, ask, cancel, or typing.
22. [x] **I3.3 — GREEN: `planAiApply('editor')` local-preview branch and save routing.**
    Replace the current `{request}`-only branch in `app.ts` with strict validation of
    the local preview payload; route the explicit save to the proposal-bound backend
    command; do not add a protocol method for the AI call itself (reuse
    `ai.prepare`/`run`/`apply`).
23. [x] **I3.4 — RED/GREEN: context, privacy, and security bounds.** Update
    `syncAiContext` to send the ordered draft ids; extend `security.ts` for the bounded
    editor improvement context and command fields; Node tests that
    `editor-security`/`optional-ai` reject a malformed preview payload, unknown tokens,
    a path in a proposal, an oversized draft order, and enforce the 2000-character
    improvement instruction bound (the legacy manual UI stays at 500, while the
    pre-existing IPC/backend manual preview bound remains 2000).
24. [x] **I3.5 — VERIFY focused.** `cd desktop-electron && npm test` for the focused
    targets (`renderer.editor*.test.mjs`, `renderer.editor-app.test.mjs`,
    `optional-ai*.test.mjs`, `editor-security.test.mjs`,
    `renderer.optional-ai-app.test.mjs`). As built, I3 landed as five work units
    (`f60f81b`, `7aef8b9`, `a8ccb5a`, `a74bbed`, `e9bccb9`) rather than one; focused runs
    per unit and an independent full offline `npm test` (480 passed, 0 skipped) both
    passed.

## Slice I4 — Integrate, verify, and document handoff

25. [x] **I4.1 — Offline gates.** Independent verifiers ran the focused Python and Node
    suites, `uv run python scripts/release_gate_check.py --run`, and
    `cd desktop-electron && npm test`; the observed result is recorded once in
    `verify-report.md`. The floor stays in
    `pyproject.toml` and `--cov-fail-under` was never passed. These gates were not re-run
    in this documentation pass.
26. [x] **I4.2 — Reconcile artifacts with observed implementation.** This documentation
    pass updated `proposal.md`, `spec.md`, `design.md`, this file, `apply-progress.md`,
    `verify-report.md`, and the prose notes in `state.yaml` from observed commit and
    offline evidence. Provider-owned SDD phase fields in `state.yaml` were deliberately
    left unadvanced.
27. [x] **I4.3 — Reconcile the durable spec.** Added the new durable capability
    `openspec/specs/electron-playlist-improvement/spec.md`, recording the as-built AI
    authorized-candidate, token, disclosure, preview, draft-only apply, and
    proposal-bound compare-and-update save rules with testable scenarios. The older
    `my-playlists-screen/spec.md` was deliberately not rewritten, and its absent "Add
    from Library" feature is not claimed to have shipped. Live provider, native-dialog,
    visual macOS, and real-library acceptance are recorded as pending evidence in
    `verify-report.md` and in the new spec's non-claims section.
28. [x] **I4.4 — Record limits.** State explicitly that mocks do not prove live provider,
    native-confirmation, or visual macOS behavior, that tokenization is pseudonymization
    and not anonymity, that saved-editor locks/excludes are absent, and that no release,
    push, PR, or merge is claimed.

## Cross-cutting rules for every slice

- [ ] RED observed as an actual failing test before the production change; GREEN from
  the focused run; REFACTOR only while green.
- [ ] No audio mutation, no DSP scope, no live Serato V2 write, no dependency change,
  no `AppState` mutation, no coverage-floor override.
- [ ] No widening of the shared `_POLICY`, the 4096-character response bound, the
  64 KiB request bound, or the global default model.
- [ ] Keep each work-unit commit at or under 400 changed lines; split further when it
  would exceed the budget. Do not compress tests or docs to fit.
- [ ] Conventional commits, no AI attribution.
