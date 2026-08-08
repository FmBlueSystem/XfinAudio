# Archive Report: Resolve Two-Axis Review Findings for Colour Strategies

**Change**: resolve-color-review-findings
**Archived to**: `openspec/changes/archive/2026-08-07-resolve-color-review-findings/`
**Archived date**: 2026-08-08
**Artifact store mode**: openspec

## What Shipped

- **Branch commit**: `f7dd244`
- **PR**: #339 merged to `main` on 2026-08-07, squashed as `201e001`
- **Version**: 1.7.3 → 1.7.4 (`uv.lock` synced)

## Verification Verdict

**PASS** — `uv run pytest -q` 1499 passed, pyright 0 errors, ruff check and
format clean, CI green on the PR.

## Artifact provenance

These artifacts were authored **retroactively**, on 2026-08-08, from the merged commit —
`AGENTS.md` requires durable `openspec/` artifacts for every non-trivial change and PR
#339 shipped without them. Every claim here is checkable against `git show 201e001`;
nothing is reconstructed from intent. Same precedent as
`2026-07-18-recommendation-scoring-correctness-fixes`, whose artifacts were also added
after the fact.

Consequence, stated plainly: these documents **record** the change, they did not steer
it. There is no RED-first TDD ledger for this change because the artifacts postdate the
work; the tests listed in `apply-progress.md` are the ones that actually shipped, and
each pins a named finding.

## Archive Contents

- [x] proposal.md — intent, the eight findings, scope boundaries, success criteria
- [x] spec.md / specs/resolve-color-review-findings/spec.md — 8 requirements (R1–R8)
- [x] design.md — alternatives for F2, F3, F6, plus the retroactive-artifacts decision
- [x] tasks.md — 13 tasks, all complete
- [x] apply-progress.md — per-finding account, test evidence, characterization exception
- [x] verify-report.md — requirement-by-requirement evidence and command results

## Specs Synced

**None.** The delta spec stays in this change folder and was **not** merged into
`openspec/specs/`. Creating a new main-spec capability now would assert a spec-tree
state that no shipped change ever established, which would contradict the point of a
retroactive record. The durable behaviour these requirements describe belongs to the
`same-color-strategy` / `same-color-energy-strategy` capabilities, whose delta specs sit
in the still-active `openspec/changes/tighten-spectral-color-filters/`; whoever archives
that change should fold R1–R8 in at that point.

## Follow-Up Items

### (a) Prep Copilot planned colour sets unanchored (CLOSED)

**Status**: Closed by PR #340, archived as `2026-08-08-prep-copilot-color-anchor`.
`PrepCopilotController.generate` took the plain records route for every strategy, so
Prep Copilot re-resolved a colour anchor per variant while the main desktop
recommendation route did not.

### (b) Duplicated candidate-route branch across the two desktop entry points (CLOSED)

**Status**: Closed on `chore/color-anchor-followups`.
Once PR #340 landed, `RecommendationService.recommend` and
`PrepCopilotController.generate` held near-verbatim copies of the same
`if strategy_name in COLOR_FILTER_STRATEGIES:` branch — precisely the drift risk F6
removed one layer down. Extracted to
`src/xfinaudio/desktop/candidate_routes.py::resolve_candidate_route`.
