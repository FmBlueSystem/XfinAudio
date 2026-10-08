# Prep AI readiness during library work

## Objective
Make the current Electron Prep optional-AI panel intelligible and preserve an entered request while a profile/library job keeps the single core busy. Once that job finishes, let the user explicitly prepare a preview; never auto-send to a provider.

## Problem, evidence, uncertainty
User screenshot shows an entered Prep request, 'Asistencia activada solo para solicitudes explícitas', selected credential source and 'No se ha comprobado la conexión', but the preview button does not activate. The first two indicators establish enabled/configured, not valid credentials. Connection check is informative, not a gate. Static code shows `gate.busy` disables all AI controls, and rendering may overwrite request text while blocked. The ongoing 10,391-track profile completion is a plausible cause, not proven live state. Do not mislabel a credential or provider issue as diagnosed.

## Authorized scope and constraints
- Only local Electron Prep AI readiness/disabled explanation and request preservation. Respect the single-job backend; do not queue, auto-run, contact, or probe the real Nan Builders provider or credential file. Consent and native confirmation stay unchanged.
- Separate linked worktree `fix/prep-ai-readiness`; never restart or mutate the running main app or its temporary profile. Work in parallel only in isolated worktrees, as requested.
- Strict TDD from repository `AGENTS.md` and project skill. Test no provider calls while busy, entered text persists, explicit reason appears, and manual preview becomes available only after readiness returns. Maintain Spanish product UI convention. Test with local mock APIs only.
- Full required gate: `uv run python scripts/release_gate_check.py --run`; no `--cov-fail-under` override. Local focused command: `cd desktop-electron && PATH="/opt/homebrew/bin:$PATH" npm test` with existing dependencies shared read-only.

## Tasks, scope and checks
- [x] **A1 — Make blocked Prep AI actionable** (delegated direct; renderer view/app plus tests). RED: 22 pass/2 fail because request textarea was disabled while busy. GREEN: request remains editable and retained through a held local job, waiting guidance appears, preview remains disabled and sends nothing, and manual preview is available after idle. Focused build/24 tests passed; full Node suite 436 passed/0 skipped. No provider or real music contacted; work-unit commit `5da83fcfa21c9ee6cb6229bdd3e72a3f046dec49`.
- [x] **A2 — Verify and document** (delegated verifier; exact-byte offline gate). Mocked busy→idle + manual preview flow: Node 436 passed/0 skipped; Python gate 4205 passed, 94.45% coverage (floor 89%), Pyright 0 errors, Ruff lint/format, smoke/docs/source hygiene and PyInstaller check-only passed (exit 0). No network, credential lookup, or live music; real provider, live UI and restart remain untested. Local commit exists; native review is deferred as `under_budget`.

## Route and delivery
A1 delegated because of multi-file writes and preparation trigger; A2 delegated verification. Forecast ~100-220 authored changed lines, delivery strategy `ask-on-risk`, branch point `f11fd3d9003f1c86668ac9683079b8aa24a15751`. User explicitly authorized local work-unit commit `5da83fcfa21c9ee6cb6229bdd3e72a3f046dec49` (`fix(ai): retain Prep request during local work`) on 2026-10-04. Native committed-range assessment: medium, 101 changed lines, `reviewDue=false`, reason `under_budget`; no native review claimed. No push/PR/merge/restart is authorized.

## Progress
- 2026-10-04: Read-only map and screenshot analysis completed. User requested parallel repair; second worktree created.
- A1 behavior and tests verified: `npm run build && node --test tests/optional-ai-view.test.mjs tests/renderer.optional-ai-app.test.mjs` — 24 passed; `XFIN_PYTHON=... PATH=/opt/homebrew/bin:$PATH npm test` — 436 passed, 0 skipped. A2 verified: offline project gate passed (4205 Python tests, 94.45% coverage, type/lint/format/smoke/docs/hygiene green). Live 10,391-track flow and credential/provider access were deliberately not tested. Local commit exists; no native review or restart yet. Project OpenSpec artifact requirement remains unresolved under the direct ODD route.

## Next step
Local work-unit commit exists, but project-required OpenSpec artifacts remain unfulfilled under the direct ODD route. Native review is deferred as `under_budget`; a later safe app restart/integration needs separate authorization. Do not push/PR/merge automatically.
