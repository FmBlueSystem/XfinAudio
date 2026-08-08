# Archive Report: Carry the Bound Colour Anchor Through Prep Copilot Variant Planning

**Change**: prep-copilot-color-anchor
**Archived to**: `openspec/changes/archive/2026-08-08-prep-copilot-color-anchor/`
**Archived date**: 2026-08-08
**Artifact store mode**: openspec

## What Shipped

- **Branch commit**: `2c2bd0d`
- **PR**: #340 merged to `main` on 2026-08-08, squashed as `53d68a6`
- **Version**: 1.7.4 → 1.7.5 (`uv.lock` synced)
- **Predecessor**: `resolve-color-review-findings` (PR #339) — this change closes that
  change's follow-up item (a)

## Verification Verdict

**PASS** — `uv run pytest -q` 1505 passed, pyright 0 errors, ruff check and format
clean, CI green on the PR.

## Artifact provenance

Authored **retroactively**, on 2026-08-08, from the merged commit — `AGENTS.md` requires
durable `openspec/` artifacts for every non-trivial change and PR #340 shipped without
them. Every claim here is checkable against `git show 53d68a6`.

Consequence, stated plainly: these documents **record** the change, they did not steer
it. There is no RED-first TDD ledger; the tests listed in `apply-progress.md` are the
ones that actually shipped, and each pins a named requirement.

## Archive Contents

- [x] proposal.md — intent, the four gaps, scope boundaries, success criteria
- [x] spec.md / specs/prep-copilot-color-anchor/spec.md — 6 requirements (R1–R6)
- [x] design.md — alternatives for anchor transport, fail-closed semantics, combo
      normalisation, and seam typing
- [x] tasks.md — 10 tasks, all complete
- [x] apply-progress.md — per-gap account, test evidence, deliberate non-changes
- [x] verify-report.md — requirement-by-requirement evidence and command results

## Specs Synced

**None**, for the same reason as the predecessor: the durable behaviour belongs to the
`same-color-strategy` / `same-color-energy-strategy` capabilities, whose delta specs sit
in the still-active `openspec/changes/tighten-spectral-color-filters/`. Creating a new
main-spec capability retroactively would assert a spec-tree state no shipped change
established. Whoever archives `tighten-spectral-color-filters` should fold R1–R6 in.

## Follow-Up Items

### (a) Duplicated candidate-route branch across the two desktop entry points (CLOSED)

**Status**: Closed on `chore/color-anchor-followups`.
After this change, `PrepCopilotController.generate` and `RecommendationService.recommend`
held near-verbatim copies of the same
`if strategy_name in COLOR_FILTER_STRATEGIES:` branch — the drift risk the shared
`COLOR_FILTER_STRATEGIES` constant removed one layer down, reintroduced one layer up.
**Action taken**: extracted to
`src/xfinaudio/desktop/candidate_routes.py::resolve_candidate_route`, which takes the two
route callables as parameters so each caller hands it its own seam. Both call sites now
resolve through it; the resolver's own contract is pinned by
`tests/test_desktop_candidate_routes.py`.

### (b) `PrepCopilotController` reached `MainWindow` privates through `_state` (CLOSED)

**Status**: Closed on `chore/color-anchor-followups`.
The controller called `self._state._desktop_recommendation_records` and
`self._state._desktop_color_anchor_candidate_context` — two private methods of another
object — while `RecommendationService` took the same two as injected callables wired in
`window_service_wiring.py`.
**Action taken**: both became required keyword-only constructor parameters, wired where
the controller is constructed in `main_window.py`. `_state` is retained for what it
legitimately provides (`_state`, `tr`, `_selected_track_controls`, `_replace_app_state`,
screens, `last_prep_copilot_plan`).
