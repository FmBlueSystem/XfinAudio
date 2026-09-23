# Verification Report: harden-release-gates

**Change**: harden-release-gates
**Branch**: `chore/harden-release-gates`
**Mode**: strict TDD
**Artifact store**: OpenSpec

## How to read the numbers in this report

Two revisions appear below, and they are not interchangeable.

| Revision | What it covers |
|---|---|
| `234d6f5` | the finished code change: WU1–WU5, measured with a clean worktree |
| `39fbeb5` | adds WU6, the documentation fix and its guard test |

The full-suite figure of 1896 was measured at `234d6f5`, before WU6 added its test. The figure
after WU6 is 1897 collected tests; WU8 re-runs the whole set over the finished tree and its result
is recorded below.

## Gate results at `234d6f5`

| Command | Result |
|---|---|
| `uv run pytest -q` | PASS — 1896 passed, 0 failed, 0 skipped, 62.98s |
| `uv run pytest --cov -q` | PASS — `TOTAL 11332 947 91.64%`; "Required test coverage of 89.0% reached" |
| `uv run pyright src tests` | PASS — 0 errors, 0 warnings |
| `uv run ruff check .` | PASS — clean |
| `uv run ruff format --check .` | PASS — 310 files already formatted |
| `uv run python scripts/release_gate_check.py --run` | PASS — exit 0; every non-audio gate PASS, sdist and wheel inspected, no project-root `build/` or `dist/` |

The release gate reported, among others: `PASS release readiness smoke`,
`PASS open-source publication docs`, `PASS publication artifact hygiene`,
`PASS source package hygiene` for both `xfinaudio-1.8.2.tar.gz` and
`xfinaudio-1.8.2-py3-none-any.whl`, `PASS PyInstaller check-only`, and
`PASS root artifact hygiene`. Its manual gate list records real Mixed In Key audio QA as
`COMPLETED`.

## Focused results at `39fbeb5`

| Command | Result |
|---|---|
| `uv run pytest -q tests/test_release_gate_check.py -k documented_verification` | PASS — 1 passed |
| `uv run pytest -q tests/test_release_gate_check.py tests/test_public_open_source_docs.py` | PASS — 21 passed |
| `uv run ruff check .` | PASS — clean |
| `uv run ruff format --check .` | PASS — 310 files already formatted |

## Gate results at the finished tree (WU8)

Measured with the nine change artifacts present in the working tree.

| Command | Result |
|---|---|
| `uv run pytest -q` | PASS — 1897 passed, 0 failed, 63.57s |
| `uv run pytest --cov -q` | PASS — `TOTAL 11332 947 91.64%`; "Required test coverage of 89.0% reached. Total coverage: 91.64%" |
| `uv run pyright src tests` | PASS — 0 errors, 0 warnings, 0 informations |
| `uv run ruff check .` | PASS — clean |
| `uv run ruff format --check .` | PASS — 310 files already formatted |
| `uv run python scripts/release_gate_check.py --run` | PASS — exit 0 |

The collected count confirms the prediction in the section above: 1896 at `234d6f5`, 1897 after
WU6 added its guard test. Coverage is unchanged at 91.64%, so the new test adds coverage without
moving the aggregate.

The release gate reported `PASS release readiness smoke`, `PASS open-source publication docs`
(24 passed), `PASS publication artifact hygiene` (5 passed), `PASS source package hygiene` after
building `xfinaudio-1.8.2.tar.gz` and `xfinaudio-1.8.2-py3-none-any.whl` from the source
distribution, `PASS PyInstaller check-only` (6.20.0), and `PASS root artifact hygiene`. Its
manual gate list records real Mixed In Key audio QA as `COMPLETED`.

These artifacts were untracked when the run above was taken. The gate was therefore run a
second time after they were committed, because committing them changes what several guards
are looking at: `openspec/` is part of the source distribution, and the publication hygiene
gate, the local-checkout reference guard and the sdist inspection all read `git ls-files`.
That second run also exited 0, with `PASS publication artifact hygiene`, `PASS source package
hygiene` for both `xfinaudio-1.8.2.tar.gz` and `xfinaudio-1.8.2-py3-none-any.whl` built from
the distribution, and `PASS root artifact hygiene`. The two guards most exposed to this
change were also run directly against the tracked set — `test_local_checkout_references.py`
and `test_publication_artifact_hygiene.py` — and pass, 11 tests.

## Each defect verified against the branch

The defects were re-verified rather than accepted from their commit messages.

| ID | Verification performed | Result |
|---|---|---|
| B1 | Created a git-ignored `.DS_Store` at the repository root — the exact file that failed the gate — and ran the hygiene suite | 5 passed; `git check-ignore` confirms the path is ignored; the file was removed afterwards |
| B2 | Read the publish workflow for the release-gate step and the tag assertion, and their order relative to the build | both present and before the build; the version step fails naming both values |
| B4 | Read `pyproject.toml` for the floor and the gate command for the flag | `fail_under = 89`; no `--cov-fail-under` in the command |
| B5 | Read the build configuration and the inspection constants | five `sdist` exclusions; `FORBIDDEN_PATH_PREFIXES` and `FORBIDDEN_PATH_PATTERNS` present |
| E1 | Read `openspec/config.yaml` | `root: .`, repository-relative, with the reasoning recorded in a comment |

## Spec compliance

Both capability deltas are new, so every requirement is an ADDED requirement.

| Capability | Requirement | Scenarios | Pinning evidence | Result |
|---|---|---:|---|---|
| release-gate-integrity | the publication gate inspects the publication tree | 2 | `test_publication_gate_reads_the_index_not_the_filesystem` drives both directions in a throwaway repository; `test_publication_tree_has_no_local_or_backup_artifacts` and `test_publication_root_has_no_local_private_handoff_files` exercise the tracked tree | COMPLIANT |
| release-gate-integrity | the coverage floor has exactly one owner | 2 | `test_coverage_floor_has_one_definition_and_cannot_sit_far_below_reality` refuses the flag and refuses a floor below 85; the gate reported the 89.0% floor reached | COMPLIANT |
| release-gate-integrity | the sdist carries no planning or review scratch | 2 | `test_sdist_configuration_excludes_scratch_before_it_is_built` and `test_inspect_sdist_rejects_planning_and_review_scratch` (six parametrized paths); the gate inspected the real sdist and wheel | COMPLIANT |
| release-gate-integrity | the publication path is gated as strongly as the pull-request path | 3 | `test_publish_workflow_runs_the_release_gate_before_publishing`, `test_publish_workflow_does_not_run_the_suite_outside_the_release_gates`, `test_publish_workflow_requires_the_tag_to_match_the_project_version`, `test_publish_workflow_declares_the_offscreen_qt_platform` | COMPLIANT |
| repository-reference-integrity | no operational file names another local checkout | 4 | six tests in `tests/test_local_checkout_references.py`, including `test_no_operational_file_points_at_another_local_checkout` and `test_referenced_change_paths_exist` | COMPLIANT |
| repository-reference-integrity | documentation does not restate an owned value | 2 | `test_documented_verification_sequence_defers_the_coverage_floor_to_pyproject`, with both directions driven by hand during WU6 | COMPLIANT |

**Compliance summary**: 6 of 6 requirements, 15 of 15 scenarios.

## What this verification does not establish

- The publish workflow's tag check is verified by **reading the workflow and by the test that
  reads its `run:` blocks**. The step was never executed against a real tag push, and no release
  was published as part of this verification.
- `uv publish` was never run. Publication authority is not exercised by this change.
- No independent or native review transaction was opened for these bytes. `state.yaml` records
  `review_status: pending`; nothing in this report should be read as a review receipt.
- The floor of 89 is verified as *reached* by the current suite, which is not the same claim as
  "89 is the right floor for future changes".

## Issues found

- **CRITICAL**: none.
- **WARNING**: none attributable to this change. The suite emits 45 pre-existing warnings from
  librosa and PySoundFile under `src/xfinaudio/audio/spectral_profile.py`, unchanged by this work.
- **FOLLOW-UP, out of scope, recorded so it is not lost**: `openspec/config.yaml` declares
  `conventions.skill_registry: .atl/skill-registry.md`, but that file does not exist and `.atl/` is
  git-ignored, so the pointer cannot resolve in a clean clone.
- **FOLLOW-UP, out of scope, recorded so it is not lost**:
  `tests/test_pyinstaller_packaging.py` reads `openspec/changes/add-loudness-module/tasks.md`,
  whose `state.yaml` records `next_recommended: archive`. Archiving that change as prescribed makes
  the read fail. `library-file-watcher-rescan` is in the same position, so the same suite will break
  twice.

## Verdict

**PASS** for the local gates, with the limits stated above and no claim of independent review.

All six requirements and fifteen scenarios are implemented and pinned by tests that fail when the
guard is removed. Two guards are driven in both directions. No file under `src/xfinaudio` changes,
so the product behaviour of the application is untouched by this change.
