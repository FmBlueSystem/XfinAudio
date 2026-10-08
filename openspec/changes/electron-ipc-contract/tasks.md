# Tasks

Work unit 1 — fail-closed dispatch and parity guard. Strict TDD is active. Delivery is two local
commits on `feat/electron-ipc-contract`; no push, PR or merge.

- [x] Slice A (documentation planning only): author proposal, spec, design and tasks with minimal
      `apply-progress.md` / `verify-report.md` placeholders; no source or test file
- [x] Slice A commit checks: `git show --stat HEAD` lists only `odd/tasks/` and the change
      directory; `git diff --name-only HEAD~1 HEAD` matches no `src/` or `tests/` path
      (observed on `2422ffc`)
- [ ] Slice A rollback: not executed — no revert was needed; the commit touches only
      `odd/tasks/` and the change directory, so no runtime, schema or dependency effect exists
- [x] RED: added `desktop-electron/tests/ipc-contract.test.mjs`; observed failure of the R1
      fail-closed assertion (no `default` arm in the `action()` switch, `main.ts:109-181`)
- [x] GREEN: added `default:throw new Error('Unsupported action');` as the final arm of `action()`
      (`main.ts`, after the `cancelCurrent` case); observed the focused test passing
- [x] TRIANGULATE: confirmed the guard fails for a removed switch case (real, temporary
      `main.ts` mutation, reverted), a removed allowlist key and a preload key/method mismatch
      (in-memory simulation through the exact guard regexes; the disallowed files were not written)
- [x] REFACTOR: extraction kept readable — a single `keysBetween` helper plus inline
      slice/`matchAll` sets; focused test stays green (63 lines, R1 assertion at line 42)
- [x] VERIFY: all four contract commands were executed and are green, recorded in
      `verify-report.md` — focused guard (RED then GREEN), full local Electron suite, Qt-free
      `scripts/electron_ci_check.py` (429/429, 0 skipped) and `release_gate_check.py --run` (exit 0)
- [x] Updated `state.yaml` to `verify: complete` (all four scoped commands observed)

## Exact commands (verify)

Focused Electron guard (smallest relevant target first):

```bash
cd desktop-electron && npm run build && node --test tests/ipc-contract.test.mjs
```

Full Electron suite (repo convention; also what CI runs through the wrapper):

```bash
cd desktop-electron && npm test
```

CI-canonical fail-closed wrapper (requires a Qt-free interpreter; writes gitignored
`.release-evidence/`):

```bash
XFIN_PYTHON=/path/to/qt-free/python python scripts/electron_ci_check.py
```

Repository gate (Python only — it does **not** execute the Electron suite):

```bash
uv run python scripts/release_gate_check.py --run
```

Coverage floor is owned by `pyproject.toml` (`[tool.coverage.report] fail_under`). Never pass
`--cov-fail-under` on a command line.

## Test runner note

The Electron suite is the authoritative runner for this change: `desktop-electron/package.json`
defines `"test": "npm run build && node --test tests/*.test.mjs"`. The Electron CI job lives in
`.github/workflows/non-audio-release-gates.yml` ("Electron migration tests") and runs
`scripts/electron_ci_check.py`, which requires `XFIN_PYTHON` and fails closed on any skip,
cancellation or TODO.

## Budget

Slice A: documentation only, under 400 added lines. Slice B: +1 production line, plus a guard test
that applied at 63 readable lines (design forecast ~45), expanded progress/report, under 400 added
lines. Slice B rollback: revert the single commit
(one-line `main.ts` removal plus the test file); no migration. Checks: the exact commands above.
