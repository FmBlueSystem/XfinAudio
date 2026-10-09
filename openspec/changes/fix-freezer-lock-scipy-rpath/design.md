# Design

## Mechanism (verified by inspection, 2026-10-08)

- `PyInstaller/building/utils.py` (`set_dylib_dependency_paths`) rewrites dependent library
  paths to `@rpath` and appends an LC_RPATH of `@loader_path` plus one `..` per parent level
  of the planned destination.
- scipy 1.17.1's arm64 wheel ships `scipy/.dylibs/libgfortran.5.dylib` with absolute install id
  `/DLC/scipy/.dylibs/libgfortran.5.dylib` (original bytes `869a6555a787…`).
- Resulting freeze contains two processed copies, byte-identical (`7900acdb3abc…`):
  `_internal/scipy/.dylibs/libgfortran.5.dylib` (contained; `../..` resolves to `_internal/`,
  passes) and `_internal/libgfortran.5.dylib` (same 2-level rpath now escapes the bundle root
  → `Runtime rpath escapes bundle`).
- numpy 2.4.6 ships no `.dylibs` directory; the offender is exclusively scipy's wheel.

## Alternatives rejected

- Post-freeze dylib surgery or patching `build.py`: mutates the sealed recipe and the audit
  contract; not legitimate release evidence.
- Bumping PyInstaller past the pinned `6.20.0`: larger blast radius, unproven against the
  audit, and unnecessary given a validated earlier set.
- Hand-editing hash-locked files: forbidden by the lock documentation (`never by hand`);
  `tests/test_headless_requirements_lock_drift.py` enforces consistency.

## Chosen fix

Restore the known-good set via the documented tooling. A throwaway `uv lock` probe
(2026-10-08) confirmed resolvability against current `pyproject.toml` ranges
(`numpy>=1.24,<3.0`; scipy transitive via `librosa>=0.10,<0.12`; numba/llvmlite transitive).
Precedent: the 2.2.0 DMG build at `6c045f3` used exactly this set and passed the identical
audit code with PyInstaller 6.20.0.

## TDD framing

- RED: `packaging/macos/build.py` on `ac4abd5` fails at the post-freeze audit
  (frozen-build log, 2026-10-08).
- GREEN: probe freeze with the restored lock passes `audit_tree`; drift tests green; full
  gate green on the fix branch.
- No new unit test is added: the regression is integration-level (wheel layout × PyInstaller
  collection) and is exercised end-to-end by the drift guard, the release gate and the DMG
  build audit itself.

## Discovery during apply: Electron version contract

`assemble` compares `node_modules/electron/dist/version` against the
`devDependencies.electron` string with `!=`. A caret range (`^43.3.0`) can never satisfy it,
and the shipped dist must reproduce exactly what the lock resolved. Decision: exact-pin the
devDependency (`43.3.0`) instead of loosening the build check — the build check encodes the
correct reproducibility intent; the range was the latent defect. `npm ci` confirms
package.json ↔ package-lock.json agreement after the pin.
