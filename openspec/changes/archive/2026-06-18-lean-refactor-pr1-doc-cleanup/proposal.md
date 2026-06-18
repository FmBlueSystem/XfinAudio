## Why

The repository has accumulated planning, scratch, and bridge documents at the root and in
`docs/plans/` that duplicate or predate the durable `openspec/` artifact trail. Removing
or relocating them reduces review surface and removes conflicting "source of truth"
documents.

## What changes

- **Move** `HARMONIC_MIXING.md` (root) → `docs/harmonic-mixing.md`. The file is referenced
  by the README, the public-open-source-docs test, the harmonic mixing doc test, and
  `scripts/source_package_hygiene_check.py`. Moving it preserves the public contract
  (README link, test assertions) and consolidates documentation under `docs/`.
- **Delete** `Integración con la función Prepare de Serato Dj .md` (33 LOC, root) —
  personal scratch notes; superseded by `docs/serato-compatibility-matrix.md` and
  `docs/serato-fixture-compatibility.md`.
- **Delete** `docs/plans/2026-06-*.md` (15 files) — planning scratchpads consumed and
  superseded by the corresponding `openspec/changes/` entries. `docs/IMPLEMENTATION_HANDOFF.md`
  is updated to drop the `docs/plans/2026-06-03-xfinaudio-mvp-sdd-tdd-plan.md` reference.
- **Delete** `docs/recommendations/next-evolution.md` — speculative, no owner.
- **Delete** `.planning/codebase/ARCHITECTURE.md` and `.planning/codebase/AGENT-DISPATCH.md`.
  Both are duplicated by `docs/IMPLEMENTATION_HANDOFF.md` and `AGENTS.md`. The 3 call sites
  (`AGENTS.md`, `openspec/config.yaml`, `.atl/skills/gentle-ai-sdd-tdd/SKILL.md`) are
  updated to drop the references.
- **Delete** `PI_CLAUDE_BRIDGE_OPUS_4_8.md` (local, 124 LOC) — untracked tooling notes;
  already in `.gitignore`.

No source code changes. No test behavior changes (the two tests that reference
`HARMONIC_MIXING.md` are updated to point at the new path; assertions stay identical).

## Non-goals

- Refactoring `main_window.py` (PR 5).
- Collapsing controller/coordinator/presenter/worker files in `desktop/` (PR 4).
- Removing `node_modules/`, `package.json`, `pnpm-lock.yaml` (PR 2).
- Trimming `scripts/` (PR 3).
- Deciding whether to keep a harmonic mixing guide at all (separate product decision).

## Impact

- Net: ~1.5k LOC removed (15 stale `docs/plans/*` + 3 root scratch files + `.planning/`
  subtree) plus 1 file moved (renamed).
- Call sites updated: `README.md` (2 lines), `tests/test_harmonic_mixing_doc.py` (1
  line), `tests/test_public_open_source_docs.py` (1 line), `scripts/source_package_hygiene_check.py`
  (1 line), `AGENTS.md` (1 line), `openspec/config.yaml` (1 line), `.atl/skills/gentle-ai-sdd-tdd/SKILL.md`
  (1 line), `docs/IMPLEMENTATION_HANDOFF.md` (1 line). Total: ~9 line changes outside
  pure deletes/moves.
- Review budget: well under 400-line cap.
- Risk: low — every change is a tracked path with a clear consumer, and every consumer
  is updated in the same commit.
