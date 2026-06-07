# Proposal: XfinAudio DJ QA Remediation

## Intent

Fix the product gaps found during real XfinAudio desktop QA so the app is not only mechanically functional, but clear, musically trustworthy, and safe for a DJ workflow.

The current desktop flow can scan/select/recommend/review/preview/export, but real QA exposed three product risks:

1. Recommendation behavior can collapse a real-library playlist to a tiny result because candidate ranking favors generic tag overlap before mix feasibility.
2. `same_energy` is presented as a strategy but does not enforce the configured energy tolerance.
3. Serato export can proceed while DJ readiness is `blocked`, which creates unsafe product authority.

This change keeps XfinAudio deterministic and metadata-first. It does not add audio DSP, AI generation, Serato database mutation, or release publication.

## Proposal Question Round

These questions are intentionally captured before implementation so the product decision points are explicit:

1. Should blocked DJ readiness always prevent export, or should a deliberate override be allowed?
2. If override is allowed, what proof is required: typed confirmation, checkbox, audit log, sidecar only, or no override in the first slice?
3. What is the minimum acceptable playlist result for the real 102 BPM anchor before the app says the recommendation is not useful?
4. Should `same_energy` preserve DJ-locked/manual-prefix tracks even when they violate tolerance?
5. Which matters more for first release confidence: safer recommendation length, clearer UI guidance, or export safety?

### Assumptions for this SDD change

- First slice blocks export when readiness is `blocked`; no override is implemented until explicitly specified and tested.
- DJ-controlled locked/manual-prefix tracks remain under DJ authority unless explicitly excluded, but generated candidates must obey strategy constraints.
- A recommendation that becomes too short must explain why rather than hiding warnings.
- Controlled E2E validation must never write to the user's real Serato library.

## Scope

### In Scope

- Restore clean automated quality gates.
- Enforce `same_energy` strategy tolerance around the selected anchor.
- Rank recommendation candidate pools by mix feasibility before generic tag overlap.
- Prevent blocked recommendations from silently exporting to Serato crates.
- Make Build, Review, Export, and Metadata screens explain decisions and next actions.
- Align public/test table aliases with the visible library table.
- Add controlled QA evidence for automated gates, E2E export safety, screenshots, and manual DJ workflow review.

### Out of Scope

- Waveform, BPM, key, or energy detection.
- AI recommendation generation.
- Serato database mutation.
- Full visual redesign of the desktop app.
- Publishing, notarization, DMG, or release claims before manual DJ QA is rerun.

## Capabilities

### New Capabilities

- `dj-recommendation-safety`: Recommendation behavior that preserves musically plausible BPM, energy, key, and tag constraints before export.
- `serato-export-safety`: Export behavior that prevents blocked DJ readiness from silently writing Serato crates.
- `desktop-workflow-guidance`: Desktop UI guidance, empty states, and decision copy that explain workflow value and next actions.
- `desktop-qa-evidence`: Automated, controlled E2E, screenshot, and manual DJ workflow evidence required before release claims.

### Modified Capabilities

- `desktop-main-window`: Public widget compatibility and visible-widget truthfulness, especially table aliases and workflow screen state.

## Approach

Use small, TDD-first slices. Fix quality gates first, then recommendation correctness, then export safety, then widget truthfulness, then UX guidance and final QA evidence.

Keep the existing PySide6 desktop architecture:

- `MainWindow` coordinates workflow state and connects screens.
- Screen widgets render view models and expose user-observable states.
- Pure recommendation/export logic stays outside Qt where possible.
- Serato export planning remains controlled and deterministic.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/xfinaudio/recommendation/playlist_service.py` | Modified | Enforce strategy energy tolerance. |
| `src/xfinaudio/desktop/recommendation_presenter.py` | Modified | Rank candidate pools by mix feasibility. |
| `src/xfinaudio/desktop/main_window.py` | Modified | Export guard, table alias truthfulness, state wiring. |
| `src/xfinaudio/desktop/screens/*` | Modified | Build, Review, Export, Metadata guidance and empty states. |
| `src/xfinaudio/desktop/*_view_model.py` | Modified | Decision copy and user-observable screen state. |
| `tests/` | Modified | Strict TDD tests for each behavior and regression. |
| `scripts/` | Created/Modified | Optional controlled QA and screenshot harnesses. |
| `docs/` | Modified if needed | Only exact behavior/workflow docs changed by the final QA slice. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Recommendation changes overfit the 102 BPM example | Medium | Add small deterministic tests plus real-library smoke evidence. |
| Export blocking frustrates DJs who knowingly want to export | Medium | First slice blocks for safety; override requires explicit future spec. |
| UI guidance becomes verbose and clutters compact desktop screens | Medium | View models expose concise decision copy; screens use progressive disclosure. |
| One large implementation overwhelms review | High | Use chained PR slices and the 400 changed-line review budget. |
| Tests interact with stale/legacy widgets | High | Align public aliases with visible widgets and test that contract. |

## Rollback Plan

Each PR slice is independently revertible:

1. Quality gate cleanup can be reverted as formatting/lint-only changes.
2. Recommendation strategy/ranking can be reverted without touching export or UI screens.
3. Export blocking can be reverted to previous export behavior if the product decision changes, while preserving tests as documentation of the safety tradeoff.
4. UX copy/view-model changes can be reverted per screen.
5. QA harness/docs can be removed without changing production behavior.

## Dependencies

- Current PySide6 desktop workflow remains the app entry point.
- Existing SQLite-backed track repository provides real saved-library records.
- Serato validation uses temporary `_Serato_/Subcrates` folders only.
- Strict TDD is enabled in `openspec/config.yaml`.

## Success Criteria

- [ ] `uv run pytest -q` passes.
- [ ] `uv run ruff check .` passes.
- [ ] `uv run ruff format --check .` passes.
- [ ] `uv run python scripts/release_gate_check.py --run` passes or records justified blockers.
- [ ] `same_energy` filters generated candidates outside anchor energy tolerance.
- [ ] Candidate pool ranking prefers BPM-feasible candidates before generic tag overlap.
- [ ] Blocked DJ readiness cannot silently export Serato crates.
- [ ] Build, Review, Export, and Metadata screens explain value and next action clearly.
- [ ] Public table aliases refer to visible widgets or expose truthful visible-widget accessors.
- [ ] Controlled E2E validation writes only to temporary Serato folders.
