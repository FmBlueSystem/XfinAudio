# Design: Drop Node toolchain

## Approach

Two `git rm` operations and one local `rm`. Zero call sites, zero source impact, zero
.gitignore change. The `.gitignore` already covers the same paths.

## Files affected

| Path             | Status    | Lines |
|------------------|-----------|-------|
| `package.json`   | tracked   | 12    |
| `pnpm-lock.yaml` | tracked   | 76    |
| `node_modules/`  | untracked | n/a   |

Total: ~88 LOC removed from tracked files; ~4 MB local directory removed.

## Step-by-step

1. `git rm package.json pnpm-lock.yaml`
2. `rm -rf node_modules/`
3. Verify:
   - `git ls-files package.json pnpm-lock.yaml` → empty.
   - `ls -d node_modules` → "No such file or directory".
   - `grep -E "package\.json|pnpm-lock|node_modules" .gitignore` → still present.
4. Run the full verification suite to confirm zero impact:
   - `uv run pytest -q`
   - `uv run ruff check .`
   - `uv run pyright src tests`
5. Single work-unit commit: `chore(tooling): drop unused Node toolchain`.

## Risks

- **None expected**. The pre-flight grep confirmed no source/test references to npm,
  pnpm, or node_modules. `.opencode/node_modules/` is a different path inside a
  gitignored directory and is not affected.

## Rollback

Single `git revert <commit-sha>` restores the previous state.
