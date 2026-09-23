# ODD feature ledger — harden-release-gates

**Branch:** `chore/harden-release-gates` (from `main` @ `490f79a`)
**Worktree:** `/Users/freddymolina/Desktop/XfinAudio/repo`
**Runtime:** macOS, Python 3.11, `uv`
**Mode:** strict TDD (RED observed before every production change)

> This ledger originally named
> `~/orca/workspaces/xfinaudio-local-main/harden-release-gates` as the worktree. Those
> clones were consolidated on 2026-09-22 into the single working clone at
> `~/Desktop/XfinAudio/repo` (see `~/Desktop/XfinAudio/CONSOLIDATION.md`); the old path
> no longer exists. Corrected here so the ledger does not send the next reader to a
> directory that is gone — the same class of stale-pointer defect this change is about.

## Why

A read-only audit of this repository found four guards that do not protect what
they claim, and one publication path with no guard at all. Each was verified by
running it, not by reading it.

| ID | Defect | Evidence |
|---|---|---|
| B1 | `tests/test_publication_artifact_hygiene.py` scans the **working tree** with `PROJECT_ROOT.rglob`, so any git-ignored `.DS_Store` fails it. It is a gate inside `scripts/release_gate_check.py:54-55`, i.e. inside the mandated `AGENTS.md` verification sequence. | `uv run pytest -q` → `1 failed, 1733 passed`. `git ls-files \| grep DS_Store` → 0. The real publication path (`scripts/source_package_hygiene_check.py`, which inspects actual sdist members) excludes `.DS_Store` correctly, so the gate fails while nothing publishable is affected. |
| B2 | `.github/workflows/publish-to-pypi.yml` runs only `uv run pytest -q` before `uv build` + `uv publish` — no pyright, no ruff, no coverage floor, no release gate, and no check that the tag matches `pyproject.toml`. | workflow file, steps at `:41-52`. The PR workflow gates all of it; the PyPI path gates almost nothing. |
| B4 | `[tool.coverage.report] fail_under = 70` against a real 91.64%. | measured on `main`: `TOTAL 11332 947 91.64%`. A 21.6-point hole. |
| B5 | The published sdist ships planning scratch: `PLAN.md`, `PLAN-REVIEW-LOG*.md`, `PLAN-docs-audit-*.md` and eight files under `docs/reviews/`. | verified with a real `uv build --sdist` + diff against `git ls-files`. `FORBIDDEN_FILE_NAMES` in the hygiene script does not cover them, so the gate passes. |
| E1 | `openspec/config.yaml:5` sets `project.root` to `/Users/freddymolina/Documents/audio` — a different, independent clone of this repository. | that path exists, is its own git checkout on a branch 324 commits behind, and was already flagged as an unfixed defect in `openspec/changes/archive/2026-07-18-recommendation-scoring-correctness-fixes/design.md:66`. |

## Tasks

- [x] 1. RED: publication gate must read the index, not the filesystem
- [x] 2. GREEN: rewrite the publication hygiene tests onto the tracked tree
- [x] 3. RED+GREEN: coverage floor guard test, then raise `fail_under` to 89
- [x] 4. RED+GREEN: forbid planning scratch in the sdist (config + hygiene script)
- [x] 5. RED+GREEN: publish workflow must run the release gate and assert the tag
- [x] 6. RED+GREEN: `openspec/config.yaml` must not name another checkout
- [x] 7. OpenSpec change artifacts (`openspec/changes/harden-release-gates/`)
- [x] 8. Full gate + release gate + evidence

## Commits

| Task | Work unit | Commit |
|---|---|---|
| 1–2 | the publication hygiene gate reads the index | `f89d082` |
| 3 | pyproject owns the coverage floor, raised to 89 | `ceb2dc2` |
| 4 | the sdist excludes planning and review scratch | `6302c3e` |
| 5 | the publish path runs the release gate and asserts the tag | `837db53` |
| 6 | `openspec/config.yaml` describes this repository | `234d6f5` |
| — | the documented verification sequence defers the floor | `39fbeb5` |
| 7 | the SDD change artifacts | `50b0b71` |
| 8 | the gate over the finished tree, and over the committed artifacts | `637b97f` |
| — | the change's own review-budget claim corrected | `26943f9` |

## Evidence

### Baseline, on `main` before any change

```
uv run pytest --cov -q
TOTAL 11332 947 91.64%
1876 passed, 45 warnings in 86.41s
```

### Branch `chore/harden-release-gates`, measured after tasks 1–6

| Command | Result |
|---|---|
| `uv run pytest -q` | 1896 passed, 0 failed, 0 skipped, 62.98s |
| `uv run pytest --cov -q` | `TOTAL 11332 947 91.64%`, floor 89 reached |
| `uv run pyright src tests` | 0 errors, 0 warnings |
| `uv run ruff check .` | clean |
| `uv run ruff format --check .` | 310 files already formatted |
| `uv run python scripts/release_gate_check.py --run` | exit 0; every non-audio gate PASS, sdist and wheel inspected, no project-root `build/` or `dist/` |

Two counts, each tied to the revision it was measured at: 1876 on `main`, 1896 after tasks
1–6, and 1897 on the finished tree — the last one being the guard test the documentation
work unit added. The floor moved 70 → 89 across the same span. The earlier draft of this
note said the change added twenty tests, which was true of tasks 1–6 and wrong about the
finished tree by one; each figure is now stated against the revision it belongs to.

Each defect was re-verified against the branch rather than accepted from the commit
message. `.DS_Store` was created at the repository root (git-ignored, and the exact
file that used to fail the gate) and the hygiene suite passed 5/5 with it present;
`.github/workflows/publish-to-pypi.yml` was read for the gate step and the tag check;
`fail_under = 89` and the five sdist `exclude` entries were read from `pyproject.toml`;
and `openspec/config.yaml` was read to confirm `root: .`.

### The finished tree (WU8)

```
uv run pytest -q                                    → 1897 passed, 0 failed, 63.57s
uv run pytest --cov -q                              → TOTAL 11332 947 91.64%; floor 89 reached
uv run pyright src tests                            → 0 errors, 0 warnings, 0 informations
uv run ruff check .                                 → clean
uv run ruff format --check .                        → 310 files already formatted
uv run python scripts/release_gate_check.py --run   → exit 0, every non-audio gate PASS
```

The gate was run three times: with the change artifacts untracked, after they were committed,
and after the change's own review-budget claim was corrected. The repeats are not ritual —
touching a tracked file changes what the guards inspect, because the publication hygiene
gate, the local-checkout reference guard and the sdist inspection all read `git ls-files`,
and `openspec/` is part of the source distribution while `odd/` is excluded from it. All
three runs exited 0 with every gate PASS. The 1897 in the block above is the second run; the
third followed only a documentation edit and its individual counts were not re-recorded, so
that figure is not claimed for it.

## Defects and where they are pinned

| ID | Fixed by | Pinned by |
|---|---|---|
| B1 | `f89d082` | `test_publication_gate_reads_the_index_not_the_filesystem` — drives both directions inside a throwaway repository, so the oracle is pinned rather than only the current tree's state |
| B2 | `837db53` | `test_publish_workflow_runs_the_release_gate_before_publishing`, `..._requires_the_tag_to_match_the_project_version`, `..._does_not_run_the_suite_outside_the_release_gates` (reads the workflow's `run:` blocks, so a comment mentioning a command is not mistaken for an invocation) |
| B4 | `ceb2dc2` | `test_coverage_floor_has_one_definition_and_cannot_sit_far_below_reality` — refuses a `--cov-fail-under` flag in the gate command, then refuses a configured floor below 85 |
| B5 | `6302c3e` | `test_sdist_configuration_excludes_scratch_before_it_is_built` (the archive must not build it in) and `test_inspect_sdist_rejects_planning_and_review_scratch` (detection is the second line of defence) |
| E1 | `234d6f5` | `tests/test_local_checkout_references.py` — refuses any tracked file outside the historical record that names that checkout, plus root/source/test path resolution |
| — | `39fbeb5` | `test_documented_verification_sequence_defers_the_coverage_floor_to_pyproject` — pins both that the documented commands pass no floor flag and that the section names `pyproject.toml` |

## Open risks

- ~~Raising the coverage floor makes every future PR pay for it.~~ **Decided.** 89 against
  91.64% leaves ~2.6 points of headroom for ordinary churn. It is deliberate slack, not a
  target to shave; the guard refuses a floor below 85.
- ~~Excluding `docs/reviews/` from the sdist also removes the loudness multi-agent review
  evidence from the published source package.~~ **Decided, and intentional.** Those documents
  remain in git and stop shipping. A source package is for building the product, not for
  carrying working notes; the exclusion is pinned by a test so it cannot silently reverse.
- `pyproject.toml`'s `[tool.hatch.build.targets.wheel]` is untouched: none of the scratch is
  inside `src/xfinaudio`, so the wheel was never affected.

## Discovered while closing this change, not fixed here

- `openspec/config.yaml:116` declares `conventions.skill_registry: .atl/skill-registry.md`,
  but that file does not exist and `.atl/` is git-ignored, so the pointer can never resolve
  in a clean clone. Same class as E1. Out of scope for this change; recorded so it does not
  disappear. (The `AGENTS.md` pointer to `.atl/skills/gentle-ai-sdd-tdd/SKILL.md` is fine:
  that file exists and is tracked.)
- `AGENTS.md` still tells a contributor to run `uv run pytest --cov -q` and separately to run
  `scripts/release_gate_check.py --run`, and the gate runner already executes the suite and the
  coverage check. Redundant rather than wrong, so it was left alone; worth folding into one
  step if the sequence is ever rewritten.
- A test reads an **active** change's artifact, so the step the SDD lifecycle itself
  prescribes breaks the suite. `tests/test_pyinstaller_packaging.py:368` reads
  `openspec/changes/add-loudness-module/tasks.md` and asserts
  `"- [x] 4.5 Packaging: FFmpeg CLI" in tasks`, but that change's `state.yaml` records
  `status: verified` and `next_recommended: archive`. Archiving it — moving it under
  `openspec/changes/archive/<date>-add-loudness-module/`, which is exactly what
  `next_recommended` asks for — makes the read fail with `FileNotFoundError`.
  `library-file-watcher-rescan` carries the same `next_recommended: archive`, so the same
  suite will break a second time. Same species as B1: a gate that fails for a reason
  unrelated to what it guards. The assertion should find the change wherever it lives, or be
  pinned to a durable capability spec under `openspec/specs/`.
