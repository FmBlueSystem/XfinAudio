# Verify Report — remove-per-query-ai-confirmation

Date: 2026-10-08 · Method: strict RED → GREEN per task (see `apply-progress.md`), full gate of record at the end.

## Requirement 1 — Persisted `autoAuthorize`, default `false`, `ai.status` exposes it, `ai.settings.update` accepts only a boolean

- Spec: `spec.md` § "Persisted automatic authorization…".
- Python: `tests/test_headless_optional_ai.py::test_auto_authorize_is_default_off_and_persists_across_facade_restarts`
  (default off, survives facade restarts); settings validation in
  `src/xfinaudio/config/settings.py` (pydantic `auto_authorize` ↔ protocol camelCase);
  status payload in `src/xfinaudio/headless/preferences.py`; protocol field set in
  `src/xfinaudio/headless/ai_protocol.py` (`autoAuthorize` optional, remaining fields still required).
- Node IPC: `tests/live-security.test.mjs::saveAiSettings accepts an optional boolean autoAuthorize and rejects other types`
  — `true`/`false` pass; `'true'`, `1`, `null`, `{}` rejected (strict boolean, fail-closed).

## Requirement 2 — WHEN `autoAuthorize` is `false`, the native confirmation dialog is required (current behavior unchanged)

- Host: `tests/optional-ai-host.test.mjs::prepare and declined native AI confirmation cannot send a provider request`
  and `::cancel or close while confirmation waits cannot turn a later yes into a request` — no `ai.run` without a
  granted dialog, and a pending confirm cannot be converted into a request after close/cancel.
- Controller: the ask notice on the dialog path still names the system dialog
  (`tests/optional-ai.test.mjs::persisted automatic authorization sends without per-request consent or dialog`
  asserts the auto path notice does NOT mention the dialog; the default path keeps the original copy, verified by
  `tests/optional-ai-view.test.mjs::the consent copy names the real authority…` dialog-path branch).

## Requirement 3 — WHEN `autoAuthorize` is `true`, no `ai.confirmation` fetch, no dialog, direct `ai.run` with `confirmed: true`

- Host: `tests/optional-ai-host.test.mjs::persisted automatic authorization sends directly without native confirmation`
  — with the dependency reporting `true`, `ask()` dispatches `['ai.run', {previewId, confirmed: true}]` and the
  confirmation dependency is never called.
- Renderer: `tests/optional-ai.test.mjs::persisted automatic authorization sends without per-request consent or dialog`
  — `canAsk` is `true` from the persisted flag alone (no consent tick), the send happens, and the notice names the
  persisted authority ("Enviando con la autorización automática guardada en Ajustes…").
- View copy: `tests/optional-ai-view.test.mjs::the consent copy names the real authority: system dialog only when
  automatic authorization is off` — RED observed against the pre-fix build (static hint wrongly claimed the dialog on
  the automatic path), GREEN after making the hint authority-aware.
- **Live evidence (real provider, one synthetic connection-test request, port 9222 CDP session):**
  1. Preview showed recipient `https://api.nan.builders/v1/chat/completions` + disclosure; the send button
     ("Probar conexión…") was enabled WITHOUT ticking consent (persisted authority accepted) — `/tmp/xfin-preview-envio.png`.
  2. After send: notice "Enviando con la autorización automática guardada en Ajustes. Cancelar no recupera los datos ya
     enviados." with the request in flight; no native dialog appeared — `/tmp/xfin-envio-auto.png`.
  3. Response received: "La conexión respondió. No se envió contenido de la biblioteca." — `/tmp/xfin-respuesta.png`.

## Requirement 4 — Survives restarts; revocable from the AI settings panel

- Python: restart-persistence test under Requirement 1.
- Node: `tests/optional-ai.test.mjs::the automatic-authorization toggle is part of the AI draft, its dirty state and
  its save`; `tests/optional-ai-view.test.mjs::automatic authorization toggle lives beside enable, drafts dirty, and
  discards cleanly` (discard restores the previous value = revocation path).
- **Live evidence:** saving persisted `auto_authorize: true` to the app data root
  (`~/Library/Application Support/XfinAudio Next/settings.json`); after killing and relaunching the app, the checkbox
  arrives checked (`/tmp/xfin-persistido-reinicio.png`). Toggle-before/after: `/tmp/xfin-antes-casilla.png`,
  `/tmp/xfin-casilla-marcada.png`, `/tmp/xfin-guardado.png`. (Screenshots are session-scoped `/tmp` artifacts.)

## Requirement 5 — Enable switch, credential selection, disclosure and payload review unchanged and required

- The whole existing AI suites stay green: Node 528/528 (0 skipped, with `XFIN_PYTHON` real interpreter), including the
  disclosure, redaction, payload-inspection and consent-reset tests; Python gate 2,823 passed, coverage 91.81%
  (floor 89.0 in `pyproject.toml`), pyright 0 errors, ruff check+format PASS, package hygiene PASS
  (`uv run python scripts/release_gate_check.py --run`, exit 0).

## Verification commands

- Focused RED: `cd desktop-electron && node --test tests/optional-ai-view.test.mjs` (17 pass + 1 fail before fix).
- Node full: `cd desktop-electron && XFIN_PYTHON=<worktree>/.venv-headless/bin/python npm test` → 528/528, 0 skipped.
- Gate of record: `uv run python scripts/release_gate_check.py --run` → exit 0 (numbers above).
