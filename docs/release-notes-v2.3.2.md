# XfinAudio 2.3.2 Release Notes

Date: 2026-10-08

## Summary

2.3.2 is an **unreleased beta/source candidate** that ships the same code changes as 2.3.1 —
the Electron 43.3.0 desktop-shell launch repair and the opt-in automatic-authorization
preference for the optional AI assistance — plus the packaging-lock repair that the 2.3.1
cycle could not include in a DMG. The `v2.3.1` tag stays on its commit as a **code-only**
release: no DMG was ever produced for it. 2.3.2 carries the first QA DMG of this cycle.

## Why 2.3.1 had no DMG, and what 2.3.2 fixes

The lockfile regeneration in commit `8d18125` downgraded the numeric stack resolved from the
documented ranges: scipy 1.18.1 → 1.17.1, numpy 2.5.3 → 2.4.6, numba 0.68.0 → 0.65.1,
llvmlite 0.50.0 → 0.47.0. The scipy 1.17.1 macOS arm64 wheel ships
`scipy/.dylibs/libgfortran.5.dylib` with an absolute install id; after PyInstaller 6.20.0
rewrites dependencies to `@rpath` with a destination-depth-relative run path, the copy that
lands at the top of `_internal/` escapes the bundle and the post-freeze native audit fails
with `Runtime rpath escapes bundle` (`packaging/macos/dependencies.py`). The 2.2.0 build
froze audit-clean with the pre-downgrade set, so 2.3.2 restores exactly that validated set:

- `scipy==1.18.1`, `numpy==2.5.3`, `numba==0.68.0`, `llvmlite==0.50.0`
  (`uv lock --upgrade-package` per package, then the documented `uv export` / `uv pip compile`
  chain; `uv pip compile` gains an explicit `--python-version 3.12` in the documented command
  so a non-3.12 default interpreter can never reject `numpy>=2.5` again).

## What changed

- `uv.lock`, `desktop-electron/requirements-headless.txt`,
  `packaging/linux/requirements-build.txt`: regenerated with the validated numeric set
  (semantic diff: those four pins only; the remaining diff is hash reordering in generated
  artifacts). `packaging/macos/requirements-build.txt` is unchanged (`macholib==1.16.4` plus
  the Linux lock).
- `tests/test_headless_requirements_lock_drift.py` stays green without modification (8 tests).
- Version moved to `2.3.2`: `pyproject.toml`, `uv.lock`, `desktop-electron/package.json`,
  `package-lock.json`, the renderer version pill, and
  `tests/test_electron_candidate_metadata.py`'s pinned candidate version.
- Documentation: `docs/release-notes-v2.3.1.md` now records that 2.3.1 stayed code-only; this
  document is new; the version cells in `docs/third-party-license-inventory.md` match the
  restored lock; the README title and its candidate paragraphs reference 2.3.2.
- `desktop-electron` `devDependencies.electron` exact-pinned to `43.3.0` (was `^43.3.0`):
  the build's assemble stage requires exact equality with the fetched Electron dist
  version, a contract the caret range could never satisfy and that no earlier build in this
  cycle had reached.
- SDD record: `openspec/changes/fix-freezer-lock-scipy-rpath/`.

## Verification

- Full gate on the fix branch: 2,823 tests passed, coverage 91.81% (floor 89.0%), pyright 0
  errors, ruff and format PASS.
- Headless lock drift tests: 8/8 passed against the regenerated locks.
- Probe freeze of the restored lock set passed the post-freeze native audit
  (`audit_tree` on the frozen core and the assembled bundle), which is the check that failed
  on `ac4abd5`.

## En español

2.3.2 es un **candidato beta de código fuente, sin release**. Incluye los mismos cambios de
código que 2.3.1 (arranque del shell de escritorio con Electron 43.3.0 y la preferencia
opt-in de autorización automática para la IA opcional) más la reparación del lock de
empaquetado que impidió producir un DMG para 2.3.1: la regeneración de locks del commit
`8d18125` había bajado el stack numérico, y la rueda de scipy 1.17.1 para macOS arm64 hace
fallar la auditoría nativa post-freeze (`Runtime rpath escapes bundle`). 2.3.2 restaura el
conjunto validado (`scipy==1.18.1`, `numpy==2.5.3`, `numba==0.68.0`, `llvmlite==0.50.0`) con
el tooling documentado, fija `--python-version 3.12` en el comando de compilación del lock de
Linux y entrega el primer DMG de QA del ciclo. La etiqueta `v2.3.1` permanece inmutable en su
commit, solo de código. El gate completo queda verde (2.823 tests, cobertura 91,81%), los
tests de drift del lock (8/8) y la sonda de freeze pasan la auditoría nativa. Los binarios V12
previos no se reconstruyen ni se renombran: conservan su versión original.
