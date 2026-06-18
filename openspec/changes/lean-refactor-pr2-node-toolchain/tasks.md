# Tasks: Drop Node toolchain

Strict TDD applies. This change is a tooling artifact removal with no behavioral
surface. The "tests" are the existing pytest/ruff/pyright suite.

## 1. Pre-flight grep

- [x] `grep -rE "npm|pnpm|node_modules" --include="*.py" --include="*.md" --include="*.yaml" --include="*.yml" --include="*.json" --include="*.toml" --include="*.sh" .` excluding `.git/`, `openspec/changes/lean-refactor-pr1-doc-cleanup/`, `openspec/changes/lean-refactor-pr2-node-toolchain/`, and the soon-to-be-deleted `pnpm-lock.yaml` and `package.json`.
- [x] Acceptance: zero hits in `src/`, `tests/`, `scripts/`, `packaging/`, `docs/`,
  `.github/`, or any tracked file other than the artifacts being deleted.

## 2. Delete tracked files

- [x] `git rm package.json pnpm-lock.yaml`

## 3. Delete local artifacts

- [x] `rm -rf node_modules/`

## 4. Verify

- [x] `git ls-files package.json pnpm-lock.yaml` → empty.
- [x] `ls -d node_modules` → "No such file or directory".
- [x] `grep -E "node_modules|package\.json|pnpm-lock" .gitignore` → still present.
- [x] `uv run pytest -q` → green.
- [x] `uv run ruff check .` → green.
- [x] `uv run pyright src tests` → green.

## 5. Commit and merge

- [x] One work-unit commit: `chore(tooling): drop unused Node toolchain`.
- [x] Push the branch.
- [x] Open PR against `tracker/lean-refactor`.
- [x] Update state.yaml → state: verifying, apply: complete.
- [x] Write apply-progress.md.
- [ ] After PR 2 merges, branch off the updated tracker for PR 3
  (`chore/trim-scripts`).
