# XfinAudio 2.3.1 Release Notes

Date: 2026-10-08

## Summary

2.3.1 is an **unreleased beta/source candidate** that repairs the desktop shell launch: the Electron runtime is pinned to 43.3.0 and the shell now starts correctly even when the launching environment leaks `ELECTRON_RUN_AS_NODE=1`. It also adds one opt-in convenience for the optional AI assistance: a persisted automatic-authorization preference that removes the per-query native confirmation dialog for users who explicitly enable it. AI remains off by default.

## Who should use it

- Source-level testers running the desktop shell on macOS from a repository worktree.
- Contributors verifying the Electron 43 launch path and the headless Python core bridge.

## What changed since 2.3.0

**Electron launch repair.** The first 2.3.0 shell launch failed with `TypeError: Cannot read properties of undefined (reading 'setName')` at `app.setName(...)`. Root cause: the launching environment (a task-runner harness that itself runs inside Electron) exports `ELECTRON_RUN_AS_NODE=1`; under it the Electron binary runs as plain Node.js, the built-in `electron` module never registers, and `require('electron')` falls through to the npm package's `index.js`, which returns the binary path string. Fixes:

- `desktop-electron` pins Electron `43.3.0` (was `44.5.1`), the runtime verified to launch in the target environment; the lockfile resolves it from the npm registry.
- `npm start` strips the leaked variable for the app process with `env -u ELECTRON_RUN_AS_NODE` (the macOS/BSD form; the project targets macOS).
- `desktop-electron/src/electron-shim.ts` turns the residual failure mode into an actionable error: when the `electron` export is a string it names the exact variable and the launch command to use, instead of a `TypeError` deep inside the app.
- `desktop-electron/src/preload.ts` imports only the `electron` built-in: the window is created with `sandbox: true`, and a sandboxed preload cannot require relative modules, so importing `./electron-shim` there killed `exposeInMainWorld` and the renderer booted without the bridge (the "Servicio local desconectado" banner). The shim stays wired in the unsandboxed main process; a new sandbox-contract guard test pins both sides.
- The source candidate version moves to `2.3.1`; `pyproject.toml`, `uv.lock`, `desktop-electron/package.json`, `package-lock.json`, the renderer version pill and this document agree.

## Optional AI: persisted automatic authorization (opt-in)

The optional Nan Builders assistance showed a native confirmation dialog on every prepared query. That per-send dialog is deliberate consent posture, but for a user who has already decided it is pure friction. This candidate adds an opt-in that removes the repeated dialog without weakening the consent architecture:

- A new persisted `autoAuthorize` preference (default off) sits in Ajustes next to the AI enable toggle. While it is off, nothing changes: every prepared query still ends in the disclosure and the native confirm dialog.
- With it on, the desktop host sends the already-prepared, opaque preview ID straight to the core's run method — no confirmation fetch, no native dialog. The disclosure was shown at prepare time; the preference only removes the repeated per-send dialog.
- The native dialog itself gains a "No volver a preguntar…" checkbox: ticking it and confirming sends that query and persists the preference (enabling the AI too) best-effort; a stale revision is ignored and Ajustes remains the reliable path to change it.
- The consent-first posture is unchanged: the AI starts disabled, credentials are selected locally, the prepared payload is reviewable before sending, and `ai.run` still accepts only a previously prepared preview ID.

## Verification recorded on this candidate

- Full gate: `uv run python scripts/release_gate_check.py --run` passed with 2,823 Python tests and 91.81% coverage (the 89% floor lives only in `pyproject.toml`), plus type check, lint, format, docs and package checks green.
- Node suite: `XFIN_PYTHON="<worktree>/.venv-headless/bin/python" npm test` passed 528/528 with 0 skipped (527 prior plus 1 new consent-copy authority test for the automatic-authorization view); the plain `npm test` run on the same tree passes 515/528 with 13 environment-conditional skips.
- Live launch on macOS: the shell window renders, the version pill shows v2.3.1, the headless core (`-m xfinaudio.headless`) spawns from the per-README `.venv-headless` provisioning, and the library connects with its full catalog after the preload fix.

## Candidate identity

**V12 and its already-built local Mac candidate are not rebuilt or relabeled by this change.** The running shell is assembled from this source tree; the earlier V12 binaries keep their original version. As with 2.3.0 this is an unreleased beta/source candidate, not an installer or a production release.

## Resumen en español

2.3.1 es un **candidato beta de código fuente, sin release**, que repara el arranque del shell de escritorio: Electron se fija en 43.3.0 y `npm start` elimina la variable heredada `ELECTRON_RUN_AS_NODE=1` con `env -u`; el shim (proceso main, sin sandbox) reporta un error accionable si el modo reaparece, y el preload con sandbox vuelve a importar solo el built-in `electron` para que el puente se exponga. La suite de Node con el intérprete real (`XFIN_PYTHON=.venv-headless/bin/python`) pasa 528/528 y el gate completo de Python queda verde (2.823 tests, cobertura 91,81%). Los binarios V12 previos no se reconstruyen ni se renombran: conservan su versión original.

## License posture

- XfinAudio source is full open source under GPL-3.0-only.
- The npm lock record set is unchanged by the Electron pin except the `electron` package itself (43.3.0); see the npm section of `docs/third-party-license-inventory.md`.
- Redistribution must comply with GPLv3 and third-party dependency obligations; no legal clearance is implied by these notes.
