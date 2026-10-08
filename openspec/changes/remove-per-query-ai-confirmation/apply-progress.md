# Apply progress: remove-per-query-ai-confirmation

Strict TDD was followed: every production edit listed below was preceded by a
confirmed-RED test in the same area (RED state observed with focused runs before
the corresponding production change; the only RED→GREEN exception is noted).

## Python core (RED: `tests/test_headless_optional_ai.py`)

- `src/xfinaudio/config/settings.py`: `AiSettings` gains `auto_authorize: bool = False`.
- `src/xfinaudio/headless/ai_protocol.py`: `ai.settings.update` accepts `autoAuthorize`.
- `src/xfinaudio/headless/optional_ai.py`: settings-update validation accepts an
  optional strict boolean and requires `revision`; persisted round-trip verified
  across facade restarts.
- `src/xfinaudio/headless/preferences.py`: `update_ai` validates/normalizes the
  field; `_ai_access` honors it; `ai.status` payload exposes `autoAuthorize`.

## Desktop host (RED: `desktop-electron/tests/optional-ai-host.test.mjs`)

- `desktop-electron/src/security.ts`: `saveAiSettings` allowlist gains
  `autoAuthorize`; non-boolean values are rejected (RED:
  `desktop-electron/tests/live-security.test.mjs`).
- `desktop-electron/src/optional-ai-host.ts`: new `autoAuthorize()` dependency;
  when it returns strictly `true`, `ask()` skips `ai.confirmation` and the dialog
  and sends `ai.run {previewId, confirmed:true}` directly. Ownership of the
  preview id is unchanged.
- `desktop-electron/src/main.ts`: the confirm dialog gains the "No volver a
  preguntar…" checkbox; ticked + confirmed persists `enabled:true,
  autoAuthorize:true` best-effort through `ai.settings.update` (stale-revision
  errors swallowed — Ajustes is the reliable path); the dependency reads the
  setting via inline read-only `ai.status`.

## Renderer (RED: `optional-ai.test.mjs`, `optional-ai-view.test.mjs`, app/draft fixtures)

- `desktop-electron/renderer/optional-ai.ts`: `AiStatus.autoAuthorize` (strict
  boolean required in `statusCopy` — fail-closed), `canAsk` accepts consent tick
  OR persisted automatic authorization, `dirty` tracks it, `save()` sends it,
  `setAutoAuthorize` guarded like `setEnabled`, ask notice names the authority in use.
- `desktop-electron/renderer/optional-ai-view.ts`: checkbox `optional-ai-auto-authorize`
  with label, hint, change wiring and snapshot sync.
- `desktop-electron/renderer/app.ts`: status fallback copy updated for the new authority.

## Live-verification follow-up (RED: `optional-ai-view.test.mjs`)

- The live CDP run exposed a truthfulness defect the suites had not covered: the
  preview consent hint statically claimed "Al continuar también se pide
  confirmación en el diálogo del sistema", which is false on the automatic
  path. Fixed with the same discipline: RED observed (focused run 17 pass +
  1 fail against the pre-fix build), then
  `desktop-electron/renderer/optional-ai-view.ts` renders the hint from
  `snapshot.autoAuthorize` (dialog wording on the dialog path, direct-send
  wording on the automatic path). GREEN: 18/18 focused, 528/528 full Node.

## Docs

- `docs/release-notes-v2.3.1.md`: path references fixed to
  `desktop-electron/src/electron-shim.ts` / `desktop-electron/src/preload.ts`
  (pre-existing doc-freshness failure), new feature section, summary and
  verification numbers refreshed.
- `README.md`, `docs/ai-settings.md`: automatic-authorization posture documented.

## RED→GREEN disclosure

- All behavior tests were written and observed failing before their production
  edit, except the doc-freshness failure of
  `test_shipped_documents_only_reference_existing_paths`, which pre-existed at
  the previous commit (0a8731b) and was fixed by correcting the two stale paths.

## Budget and constraints

- Change stays within the 400-line review budget (see `git diff --stat`).
- No audio mutation, no DSP scope, no live Serato DB V2 writes, immutable
  `AppState` (`model_copy(update=...)`), no project-root `build/`/`dist/`.
