# Tasks: Documentation cleanup

Strict TDD applies. This change is a documentation move + delete with no behavioral
surface. The "tests" for each task are the existing regression tests at the new path
and the release-gate hygiene check.

## 1. Pre-flight grep

- [x] Run `grep -rE "HARMONIC_MIXING|Integración con la función Prepare|next-evolution|\.planning/codebase|docs/plans" .` excluding `.git`, `__pycache__`, and the change directory itself.
- [x] Confirm the only hits are the 8 call sites documented in `design.md` (plus
  `openspec/changes/lean-refactor-pr1-doc-cleanup/` and any archived openspec change that
  already references them — these are history and stay).
- [x] Acceptance: the call site list matches the design.

## 2. Move `HARMONIC_MIXING.md` and update call sites

- [x] `git mv HARMONIC_MIXING.md docs/harmonic-mixing.md`
- [x] Update `README.md`: change both `[HARMONIC_MIXING.md](HARMONIC_MIXING.md)` references
  to `[harmonic mixing guide](docs/harmonic-mixing.md)` (EN line) and the equivalent ES
  line.
- [x] Update `tests/test_harmonic_mixing_doc.py`:
  `DOC = PROJECT_ROOT / "docs" / "harmonic-mixing.md"`
- [x] Update `tests/test_public_open_source_docs.py`: change
  `"[HARMONIC_MIXING.md](HARMONIC_MIXING.md)"` to
  `"[docs/harmonic-mixing.md](docs/harmonic-mixing.md)"`.
- [x] Update `scripts/source_package_hygiene_check.py`: change the required-file list
  entry `"HARMONIC_MIXING.md"` to `"docs/harmonic-mixing.md"`.

## 3. Delete the planning scratchpads

- [x] `git rm docs/plans/2026-06-*.md`
- [x] `git rm docs/recommendations/next-evolution.md`
- [x] Update `docs/IMPLEMENTATION_HANDOFF.md`: drop the bullet referencing
  `docs/plans/2026-06-03-xfinaudio-mvp-sdd-tdd-plan.md`.

## 4. Delete the internal planning tree

- [x] `git rm .planning/codebase/ARCHITECTURE.md .planning/codebase/AGENT-DISPATCH.md`
- [x] Update `AGENTS.md`: drop the `.planning/codebase/ARCHITECTURE.md` bullet from the
  Related documents section.
- [x] Update `openspec/config.yaml`: drop the `planning_history:` line under the
  `openspec/` config (or set it to `null` if the schema requires the key).
- [x] Update `.atl/skills/gentle-ai-sdd-tdd/SKILL.md`: drop the
  `.planning/codebase/ARCHITECTURE.md` bullet from the Related documents section.

## 5. Delete the scratch root file

- [x] `git rm "Integración con la función Prepare de Serato Dj .md"`
- [x] `rm PI_CLAUDE_BRIDGE_OPUS_4_8.md` (untracked; do not stage).

## 6. Verify

- [x] `git ls-files HARMONIC_MIXING.md .planning docs/plans docs/recommendations` → empty.
- [x] `git ls-files docs/harmonic-mixing.md` → exactly one line.
- [x] `git status --porcelain` shows no untracked file in the root other than the
  change dir and the existing `.opencode/` + `opencode.json` (which are pre-existing
  untracked).
- [x] `uv run pytest tests/test_harmonic_mixing_doc.py tests/test_public_open_source_docs.py -q` → green.
- [x] `uv run pytest -q` → green.
- [x] `uv run ruff check .` → green.
- [x] `uv run pyright src tests` → green.
- [x] `uv run python scripts/source_package_hygiene_check.py` → green.

## 7. Commit and merge

- [x] One work-unit commit:
  `chore(docs): consolidate harmonic guide and drop stray planning`.
- [x] Push the branch.
- [x] Open PR against `tracker/lean-refactor` (not `main`).
- [x] Update `state.yaml` → `state: verifying`, write `apply-progress.md`,
  leave `verify-report.md` for the next phase.
- [x] After PR 1 merges, branch off the updated tracker for PR 2
  (`chore/drop-node-toolchain`).
