# Tasks: XfinAudio DJ QA Remediation

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 900-1600 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 quality baseline -> PR 2 recommendation correctness -> PR 3 export safety -> PR 4 widget truthfulness -> PR 5 UX guidance -> PR 6 QA evidence |
| Delivery strategy | auto-chain |
| Chain strategy | feature-branch-chain |

Decision needed before apply: No
Chained PRs recommended: Yes
400-line budget risk: High
Chain strategy: feature-branch-chain

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Restore clean automated gates | PR 1 | Lint/format only, no behavior changes. |
| 2 | Enforce same-energy strategy | PR 2 | Strict TDD unit slice. |
| 3 | Rank pool by mix feasibility | PR 2 | Same PR as recommendation correctness if size remains acceptable. |
| 4 | Block unsafe Serato export | PR 3 | Safety boundary with UI and defensive guard. |
| 5 | Align visible widget aliases | PR 4 | Prevent false E2E confidence. |
| 6 | Explain Build workflow | PR 5a | May split UX PRs by screen if line budget grows. |
| 7 | Explain Review workflow | PR 5b | Decision-first Review state. |
| 8 | Explain Export and Metadata states | PR 5c | Empty/help states and Serato guidance. |
| 9 | Final desktop QA evidence | PR 6 | Automated gates, controlled E2E, screenshots/manual evidence. |

## Phase 1: Quality Baseline

- [x] 1.1 Confirm current failures with `uv run ruff check .` and `uv run ruff format --check .`.
- [x] 1.2 Fix line length in `src/xfinaudio/desktop/main_window.py` without behavior changes.
- [x] 1.3 Move imports above constants in `src/xfinaudio/desktop/screens/library_screen.py`.
- [x] 1.4 Break `_TRANSITION_COLUMNS` in `src/xfinaudio/desktop/screens/review_screen.py`.
- [x] 1.5 Remove unused `threading`, sort imports, and break long assertion in `tests/integration_flow.py`.
- [x] 1.6 Run formatter only on the seven files identified by format check.
- [x] 1.7 Verify `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest -q`.

## Phase 2: Recommendation Safety

- [x] 2.1 RED: Add `tests/test_playlist_strategies.py::test_same_energy_filters_candidates_outside_anchor_energy_tolerance` and confirm it fails.
- [x] 2.2 GREEN: Update `src/xfinaudio/recommendation/playlist_service.py` to enforce `strategy.energy_tolerance` after anchor resolution.
- [x] 2.3 REFACTOR: Preserve explicit DJ-controlled paths and add clear warning copy for filtered candidates or missing anchor energy.
- [x] 2.4 Verify `uv run pytest tests/test_playlist_strategies.py tests/test_playlist_service.py -q` and full gates.
- [x] 2.5 RED: Add `tests/test_recommendation_presenter.py::test_pool_prefers_bpm_feasible_candidate_over_generic_tag_overlap` and confirm it fails.
- [x] 2.6 GREEN: Update `src/xfinaudio/desktop/recommendation_presenter.py` ranking to bucket BPM feasibility before generic tag overlap.
- [x] 2.7 REFACTOR: Keep ranking deterministic with key compatibility, meaningful tags, energy distance, BPM distance, and path tie-breaker.
- [x] 2.8 Verify with unit tests and the real-library smoke check for the 102 BPM anchor.

## Phase 3: Export Safety

- [x] 3.1 RED: Add `tests/test_main_window.py::test_main_window_blocks_serato_export_when_dj_readiness_is_blocked` and confirm it fails.
- [x] 3.2 GREEN: Disable export in view state when readiness is blocked while keeping preview enabled.
- [x] 3.3 GREEN: Add defensive guard in `MainWindow.export_recommendation_to_serato()` or equivalent export path.
- [x] 3.4 REFACTOR: Ensure blocked guidance says `Resolve blocked readiness checks before exporting.` or equivalent tested copy.
- [x] 3.5 Verify blocked export does not write crates and non-blocked fixture still writes to controlled temp Serato target.

## Phase 4: Visible Widget Truthfulness

- [x] 4.1 RED: Add a test proving `window.tracks_table` is the visible library screen table or that the replacement visible accessor is used.
- [x] 4.2 GREEN: Update `src/xfinaudio/desktop/main_window.py` to make public table aliases truthful.
- [x] 4.3 REFACTOR: Remove or isolate stale legacy table construction if tests allow.
- [x] 4.4 Verify `tests/test_visual_integration.py` and `tests/test_main_window.py`.

## Phase 5: Build Workflow Guidance

- [x] 5.1 RED: Add view-model tests for anchor summary, strategy explanation, constraint explanation, and recommendation-vs-Prep-Copilot copy.
- [x] 5.2 GREEN: Update `src/xfinaudio/desktop/build_view_model.py` with tested guidance state.
- [x] 5.3 GREEN: Update `src/xfinaudio/desktop/screens/build_screen.py` to render the guidance.
- [x] 5.4 RED/GREEN: Disable or hide variant actions until variants exist.
- [x] 5.5 RED/GREEN: Show concise generated recommendation summary after recommendation.
- [x] 5.6 Verify Build view-model and visual integration tests.

## Phase 6: Review Workflow Guidance

- [x] 6.1 RED: Add Review view-model tests for `Ready to export`, `Needs review before export`, and `Blocked: do not export yet` states.
- [x] 6.2 GREEN: Update `src/xfinaudio/desktop/review_view_model.py` decision state.
- [x] 6.3 GREEN: Update `src/xfinaudio/desktop/screens/review_screen.py` so decision banner appears before detail tables.
- [x] 6.4 Verify offscreen screenshot evidence or equivalent rendered inspection.

## Phase 7: Export and Metadata Guidance

- [x] 7.1 RED: Add Export view-model tests for destination format, preview/no-write guidance, and Serato verification instructions.
- [x] 7.2 GREEN: Update `src/xfinaudio/desktop/export_view_model.py` and `src/xfinaudio/desktop/screens/export_screen.py`.
- [x] 7.3 RED: Add Metadata view-model tests for missing metadata repair-loop guidance.
- [x] 7.4 GREEN: Update `src/xfinaudio/desktop/metadata_view_model.py` and `src/xfinaudio/desktop/screens/metadata_screen.py`.
- [x] 7.5 Verify targeted tests and full gates.

## Phase 8: Final QA Evidence

- [x] 8.1 Run `uv run pytest -q`.
- [x] 8.2 Run `uv run ruff check .`.
- [x] 8.3 Run `uv run ruff format --check .`.
- [x] 8.4 Run `uv run python scripts/release_gate_check.py --run` or record blocker.
- [x] 8.5 Run controlled E2E export using temporary `_Serato_/Subcrates` only.
- [x] 8.6 Capture screenshots for changed screens or record equivalent visual evidence.
- [x] 8.7 Manually inspect Build, Review, Export, and Metadata workflow clarity.
- [x] 8.8 Create `verify-report.md` with requirement-by-requirement evidence.

## Commit Boundaries

Use conventional commits only. Never add AI attribution. Use feature-branch-chain: PR 1 targets the tracker branch, each later PR targets the immediate previous PR branch, and only the tracker branch merges to main.

- PR 1: `chore: restore clean quality gates`
- PR 2: `fix: improve recommendation safety`
- PR 3: `fix: prevent blocked recommendations from exporting`
- PR 4: `refactor: align main window table aliases with visible screens`
- PR 5: `feat: clarify desktop workflow guidance`
- PR 6: `test: add desktop workflow QA evidence`
