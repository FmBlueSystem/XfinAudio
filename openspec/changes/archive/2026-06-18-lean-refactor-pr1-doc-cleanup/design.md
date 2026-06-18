# Design: Documentation cleanup

## Approach

Move one public doc into `docs/`, then perform a pure deletion pass. Every call site is
updated in the same commit. All changes are idempotent and trivially reversible from git
history.

## Files affected

### Moves (1)

| From                       | To                            | Reason                                       |
|----------------------------|-------------------------------|----------------------------------------------|
| `HARMONIC_MIXING.md`       | `docs/harmonic-mixing.md`     | Consolidate public docs under `docs/`.       |

### Call site updates (8)

| File                                                        | Change                              |
|-------------------------------------------------------------|-------------------------------------|
| `README.md` (2 lines)                                       | Link target → `docs/harmonic-mixing.md` |
| `tests/test_harmonic_mixing_doc.py` (1 line)                | `DOC = PROJECT_ROOT / "docs/harmonic-mixing.md"` |
| `tests/test_public_open_source_docs.py` (1 line)            | Link string → `docs/harmonic-mixing.md` |
| `scripts/source_package_hygiene_check.py` (1 line)          | Required file → `docs/harmonic-mixing.md` |
| `AGENTS.md` (1 line)                                        | Remove `.planning/codebase/ARCHITECTURE.md` reference |
| `openspec/config.yaml` (1 line)                            | Remove `planning_history` field      |
| `.atl/skills/gentle-ai-sdd-tdd/SKILL.md` (1 line)           | Remove `.planning/codebase/ARCHITECTURE.md` reference |
| `docs/IMPLEMENTATION_HANDOFF.md` (1 line)                   | Remove `docs/plans/2026-06-03-xfinaudio-mvp-sdd-tdd-plan.md` reference |

### Pure deletes

| Path                                                   | Status    | Notes |
|--------------------------------------------------------|-----------|-------|
| `Integración con la función Prepare de Serato Dj .md`  | tracked   | scratch, superseded by `docs/serato-*.md` |
| `docs/plans/2026-06-*.md` (15 files)                    | tracked   | superseded by `openspec/changes/` |
| `docs/recommendations/next-evolution.md`                | tracked   | speculative |
| `.planning/codebase/ARCHITECTURE.md`                    | tracked   | duplicated by `docs/IMPLEMENTATION_HANDOFF.md` and `AGENTS.md` |
| `.planning/codebase/AGENT-DISPATCH.md`                  | tracked   | dispatch log, no longer needed |
| `PI_CLAUDE_BRIDGE_OPUS_4_8.md`                          | untracked | tooling notes, already in `.gitignore` |

Total: ~1.5k LOC removed across 18 paths, 1 path moved, 8 call sites updated (~11 LOC).

## Step-by-step

1. `git mv HARMONIC_MIXING.md docs/harmonic-mixing.md`
2. Update `README.md` (2 link lines: EN + ES) to point at `docs/harmonic-mixing.md`.
3. Update `tests/test_harmonic_mixing_doc.py` to read `docs/harmonic-mixing.md`.
4. Update `tests/test_public_open_source_docs.py` to expect the new link target.
5. Update `scripts/source_package_hygiene_check.py` to require `docs/harmonic-mixing.md`.
6. `git rm` the 15 `docs/plans/2026-06-*.md` files plus `docs/recommendations/next-evolution.md`.
7. `git rm` `.planning/codebase/ARCHITECTURE.md` and `AGENT-DISPATCH.md`.
8. Update `AGENTS.md`, `openspec/config.yaml`, `.atl/skills/gentle-ai-sdd-tdd/SKILL.md` to
   drop the `.planning/codebase/` references.
9. Update `docs/IMPLEMENTATION_HANDOFF.md` to drop the `docs/plans/2026-06-03-xfinaudio-mvp-sdd-tdd-plan.md` reference.
10. `git rm "Integración con la función Prepare de Serato Dj .md"`.
11. `rm PI_CLAUDE_BRIDGE_OPUS_4_8.md` (untracked).
12. Verify:
    - `git ls-files HARMONIC_MIXING.md .planning docs/plans docs/recommendations` → empty.
    - `git ls-files docs/harmonic-mixing.md` → one line.
    - `uv run pytest tests/test_harmonic_mixing_doc.py tests/test_public_open_source_docs.py -q` → green.
    - `uv run pytest -q` → green.
    - `uv run ruff check .` → green.
    - `uv run pyright src tests` → green.
13. Single work-unit commit: `chore(docs): consolidate harmonic guide and drop stray planning`.

## Risks

- **README broken link**: both the EN and ES link lines must be updated; missing the ES
  line is a real risk. The apply step MUST read the file and confirm both updates.
- **Test path drift**: the `DOC` constant in `test_harmonic_mixing_doc.py` and the
  required-fragments string in `test_public_open_source_docs.py` must be updated
  together; one without the other breaks CI.
- **source_package_hygiene_check.py**: this is a release-gate script, not a test. The
  apply step MUST run it standalone to confirm the new required file is detected.

## Rollback

Single `git revert <commit-sha>` restores the previous state. The moved file is
preserved with history (`git mv` keeps the rename blob in place).
