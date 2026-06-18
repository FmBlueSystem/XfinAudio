# Apply Progress: lean-refactor-pr1-doc-cleanup

## Status

- State: apply complete; verify in progress
- Branch: `chore/delete-stray-root-docs`
- Target: `tracker/lean-refactor`
- Chain strategy: `feature-branch-chain`
- Commit: `7f73d13e27861ae55ffe56b675b6d3ddb61bbaeb`
- Push: pushed to `origin/chore/delete-stray-root-docs`

## Completed work

- Moved `HARMONIC_MIXING.md` to `docs/harmonic-mixing.md` without changing document content.
- Updated harmonic guide call sites in `README.md`, harmonic/public docs tests, and source package hygiene check.
- Deleted stale `docs/plans/2026-06-*.md`, `docs/recommendations/next-evolution.md`, `.planning/codebase/*`, and the Serato Prepare scratch root doc.
- Removed the untracked `PI_CLAUDE_BRIDGE_OPUS_4_8.md` working-tree note.
- Dropped `.planning/codebase/` references from project governance/config files.

## Verification

| Check | Result |
|---|---|
| Pre-flight grep | Pass; found documented call sites plus extra tracked references handled below; `.venv` contained stale installed metadata and was ignored as non-repo output. |
| `git ls-files HARMONIC_MIXING.md .planning docs/plans docs/recommendations` | Pass; empty. |
| `git ls-files docs/harmonic-mixing.md` | Pass; exactly `docs/harmonic-mixing.md`. |
| `git status --porcelain` | Pass; only expected untracked local OpenCode/OpenSpec files before artifact update. |
| `uv run pytest tests/test_harmonic_mixing_doc.py tests/test_public_open_source_docs.py -q` | Pass; 7 passed. |
| `uv run pytest tests/test_open_source_license_docs.py -q` | Pass after updating stale plan assertions; 9 passed. |
| `uv run pytest -q` | Pass; 861 passed, 4 warnings. |
| `uv run ruff check .` | Pass. |
| `uv run pyright src tests` | Pass; 0 errors. |
| `uv run python scripts/source_package_hygiene_check.py` | Pass. |

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 1. Pre-flight grep | N/A | Repository check | ✅ `7 passed` targeted docs baseline | ✅ Grep exposed stale references before edits | ✅ Re-grep clean outside ignored/non-repo paths | ➖ Structural check | ➖ None needed |
| 2. Move harmonic guide | `tests/test_harmonic_mixing_doc.py`, `tests/test_public_open_source_docs.py`, `scripts/source_package_hygiene_check.py` | Unit/release-gate | ✅ `7 passed` baseline | ✅ Existing tests would fail after move until paths changed | ✅ Targeted tests passed | ✅ Hygiene check required new path in package artifacts | ➖ None needed |
| 3. Delete planning scratchpads | `tests/test_open_source_license_docs.py` | Unit/docs | ✅ Full suite exposed stale plan expectations | ✅ Full suite failed on deleted plan references | ✅ Updated assertions passed | ✅ Full suite passed | ➖ None needed |
| 4. Delete internal planning tree | Repository git checks | Repository check | ✅ Pre-flight grep identified references | ✅ `git ls-files .planning` would fail until deletion | ✅ Required git check empty | ➖ Structural check | ➖ None needed |
| 5. Delete scratch root file | Repository git/status checks | Repository check | ✅ Pre-flight grep identified root scratch file | ✅ Root file existed before deletion | ✅ Required status/file checks passed | ➖ Structural check | ➖ None needed |
| 6. Verify | Full verification commands | Integration/release-gate | ✅ Targeted tests green first | ✅ Initial full suite found extra stale test call sites | ✅ All required commands passed after fixes | ✅ Targeted + full + hygiene covered repo/package paths | ➖ None needed |
| 7. Commit and merge | Git/GitHub | Workflow | ✅ Diff/log/status reviewed before commit | ✅ Commit absent before workflow step | ✅ Commit and push succeeded | ➖ Single work-unit commit | ➖ None needed |

## Deviations / extra call sites

- `docs/restart-handoff-2026-06-03.md` had a tracked `HARMONIC_MIXING.md` reference and was updated to the new path.
- `docs/IMPLEMENTATION_HANDOFF.md` also listed `HARMONIC_MIXING.md`; it was updated while removing the planned `docs/plans/...` bullet.
- `tests/test_open_source_license_docs.py` referenced deleted `docs/plans/*` files; it was updated to assert the stale plans are absent and to read durable docs instead.
- `.venv/.../METADATA` had stale installed README metadata from the editable package; it is outside tracked source and was not edited.

## PR

PR creation attempted after push. `gh pr create --base tracker/lean-refactor --head chore/delete-stray-root-docs` failed because GitHub reported `Base ref must be a branch` / no base SHA for `tracker/lean-refactor`. Placeholder: https://github.com/FmBlueSystem/XfinAudio/pull/new/chore/delete-stray-root-docs (target should be `tracker/lean-refactor` once the tracker branch exists remotely).
