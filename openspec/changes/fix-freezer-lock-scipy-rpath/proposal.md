# Proposal: restore validated freezer lock versions (fix DMG blocker for v2.3.2)

## Problem

`packaging/macos/build.py` fails deterministically on commit `ac4abd5` (tag `v2.3.1`) during the
post-freeze native audit with `Runtime rpath escapes bundle` on `_internal/libgfortran.5.dylib`
(evidence: frozen-build log, 2026-10-08). No DMG can be produced from the tagged commit.

## Root cause

Commit `8d18125` regenerated the freezer locks and downgraded the numeric stack:
scipy 1.18.1→1.17.1, numpy 2.5.3→2.4.6, numba 0.68.0→0.65.1, llvmlite 0.50.0→0.47.0.
The scipy 1.17.1 macOS arm64 wheel ships `scipy/.dylibs/libgfortran.5.dylib` with an absolute
install id (`/DLC/scipy/.dylibs/...`). PyInstaller 6.20.0 collects that dylib twice; the copy
flattened to `_internal/` keeps an LC_RPATH computed for the two-level-deep destination
(`@loader_path/../..`), which escapes the bundle root and is rejected by `audit_binary`.

## Proposed change

Restore the previously validated numeric set (proven audit-clean at `6c045f3`, the 2.2.0 DMG
build, with identical audit code and the same PyInstaller 6.20.0): `scipy==1.18.1`,
`numpy==2.5.3`, `numba==0.68.0`, `llvmlite==0.50.0` — regenerated through the documented
tooling (uv.lock → headless export → compiled Linux lock), never by hand. Bump the application
version 2.3.1 → 2.3.2 and mark 2.3.1 in the release notes as a code-only release without DMG.

## Decision

Maintainer-approved in session (options: fix + re-release as v2.3.2 [chosen] / defer DMG /
move the pushed tag). Tag `v2.3.1` remains untouched; `v2.3.2` is the DMG release cut from
this fix after green gates and CI.

## Amendment (2026-10-08, apply phase)

The first probe that cleared the post-freeze audit reached `assemble` for the first time in
this cycle and exposed a latent packaging contract: `build.py::assemble` requires exact
equality between the fetched Electron `dist/version` and
`desktop-electron/package.json`'s `devDependencies.electron`, which carried the range
`^43.3.0`. The v2.3.1 build never reached this line (it failed at the audit), so the
contract had never been exercised. Resolution: exact-pin `electron` to `43.3.0` in
`package.json` and `package-lock.json` (reproducible desktop-shell builds); validated by
`npm ci` (lock agreement) and the build re-run. Scope addition: two-byte pin, no new
dependency.
