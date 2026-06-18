## Why

XfinAudio is a Python project (`pyproject.toml` + `uv`). It also carries a
`package.json` + `pnpm-lock.yaml` lockfile and a `node_modules/` directory that are
NOT used by the application: no source file references `npm`, `pnpm`, or
`node_modules`, and no `pnpm` script is invoked by CI, packaging, or release
(`scripts/` and `packaging/` are all Python). The Node artifacts are inert and
misleading — they suggest a polyglot toolchain that does not exist.

## What changes

- **Delete** `package.json` (12 LOC) and `pnpm-lock.yaml` (76 LOC).
- **Delete** `node_modules/` (local-only, already gitignored).
- **Verify** `.gitignore` already lists `node_modules/`, `package.json`, `pnpm-lock.yaml` —
  no .gitignore change required.

No source code changes. No test changes. No public API impact.

## Non-goals

- Refactoring `main_window.py` (PR 5).
- Collapsing controller/coordinator/presenter/worker files in `desktop/` (PR 4).
- Trimming `scripts/` (PR 3).
- Re-introducing a Node-based build, lint, or test runner.

## Impact

- Net: ~88 LOC removed from tracked files, 1 large untracked directory removed locally.
- Review budget: trivially under 400-line cap.
- Risk: zero (no consumer; .gitignore already correct).
