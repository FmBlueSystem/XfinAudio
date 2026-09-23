# Apply Progress: harden-release-gates

## Status

WU1–WU6 are implemented on `chore/harden-release-gates`, one commit each. WU7 is this directory.
WU8, the final gate over the finished tree, passed; its results are below.

## Provenance of the evidence in this file

This change was implemented across two sessions, and not every work unit was observed by the same
reader. Stating that plainly is part of the evidence.

- **WU1–WU5** were implemented by the session that produced the orchestration ledger at
  `odd/tasks/harden-release-gates.md`. That ledger records RED before each production change. Those
  observations are reproduced here as **recorded by that session**, not re-observed by this one.
- What this session did with WU1–WU5 is different and is recorded per work unit below: it re-read
  the artifact each fix governs, and for B1 it reproduced the original failing condition exactly.
- **WU6** was implemented by this session. Its RED, its GREEN, and both mutation directions were
  observed here.
- **WU8** was executed as an independent read-only verification pass over this branch.

No RED output is invented for a work unit whose RED nobody present observed.

## WU1 — the publication gate reads the index (B1) — `f89d082`

Recorded defect: the gate rglobbed the working tree, so a git-ignored `.DS_Store` failed it inside
the mandated verification sequence, while the real publication path already excluded that file.

Recorded RED: `uv run pytest -q` → `1 failed, 1733 passed`.

Verified in this session by reproducing the failing condition:

```
git check-ignore -v .DS_Store        → .gitignore:11:.DS_Store	.DS_Store
touch .DS_Store                      → present at the repository root
git status --porcelain | grep -c DS_Store  → 0   (invisible to git)
uv run pytest -q tests/test_publication_artifact_hygiene.py → 5 passed
```

The file was removed afterwards. The gate now passes with the exact file that used to fail it.

Pinning tests: `test_publication_gate_reads_the_index_not_the_filesystem`,
`test_publication_tree_has_no_local_or_backup_artifacts`,
`test_publication_root_has_no_local_private_handoff_files`.

## WU2 — one owner for the coverage floor (B4) — `ceb2dc2`

Recorded defect: the floor existed twice, and the command-line flag overrode the configuration.

Recorded RED: a test that fails while the gate command still passes `--cov-fail-under`.

Verified in this session by reading the governed artifacts:

```
scripts/release_gate_check.py → CommandGate("tests and coverage", ["uv", "run", "pytest", "--cov", "-q"])
                                with a comment stating no flag is passed on purpose
pyproject.toml               → fail_under = 89
uv run pytest --cov -q       → Required test coverage of 89.0% reached. Total coverage: 91.64%
```

Pinning tests: `test_coverage_floor_has_one_definition_and_cannot_sit_far_below_reality`.

## WU3 — the sdist excludes scratch (B5) — `6302c3e`

Recorded defect: a real sdist shipped `PLAN.md`, the `PLAN-REVIEW-LOG*` files and `docs/reviews/`.

Recorded RED: a test that fails because the inspection does not refuse those paths.

Verified in this session by reading the governed artifacts:

```
scripts/source_package_hygiene_check.py → FORBIDDEN_PATH_PREFIXES = ("docs/reviews", "docs/superpowers", "odd")
                                          FORBIDDEN_PATH_PATTERNS = ("PLAN*.md", "SPEC-*.md")
pyproject.toml                          → [tool.hatch.build.targets.sdist] excludes = [
                                            "/PLAN*.md", "/SPEC-*.md", "/docs/reviews",
                                            "/docs/superpowers", "/odd" ]
release gate                            → PASS source package hygiene: inspected xfinaudio-1.8.2.tar.gz
                                            and xfinaudio-1.8.2-py3-none-any.whl
```

Both halves are pinned: `test_sdist_configuration_excludes_scratch_before_it_is_built` proves the
archive cannot build it in, and `test_inspect_sdist_rejects_planning_and_review_scratch` proves
detection still works across six parametrized scratch paths.

## WU4 — the publication path is gated (B2) — `837db53`

Recorded defect: the publish workflow ran only the suite before building and publishing.

Recorded RED: tests that fail while the workflow has no release-gate step and no tag assertion.

Verified in this session by reading the workflow:

```
.github/workflows/publish-to-pypi.yml
→ on: push: tags: ["v*"]
→ step "Require the tag to match the project version": reads version from pyproject.toml,
  fails with "error: tag ${GITHUB_REF_NAME} does not match pyproject.toml ${version}"
→ step "Run non-audio release gates": uv run python scripts/release_gate_check.py --run
  --report-json .release-evidence/release-gate-report.json
→ both steps precede the build and publish steps
```

Pinning tests: `test_publish_workflow_runs_the_release_gate_before_publishing`,
`test_publish_workflow_requires_the_tag_to_match_the_project_version`,
`test_publish_workflow_does_not_run_the_suite_outside_the_release_gates`.

## WU5 — one repository (E1) — `234d6f5`

Recorded defect: three live files pointed at a second, independent clone.

Recorded RED: a test that fails because `project.root` is an absolute machine-local path.

Verified in this session by reading the config and the guard:

```
openspec/config.yaml → root: .     (repository-relative, with the reasoning in a comment)
tests/test_local_checkout_references.py → HISTORICAL_PREFIXES = ("openspec/changes/", "docs/reviews/")
                                          MACHINE_LOCAL_CHECKOUT assembled rather than written
                                          literally, so the tracked guard does not flag itself
```

Pinning tests: six tests in `tests/test_local_checkout_references.py`.

## WU6 — documentation defers to the owner — `39fbeb5`

Defect found while closing this change: removing the flag from the gate command left the same flag
in `AGENTS.md`, the file a contributor is told to follow. Following the documented sequence would
have lowered the floor from 89 to 70.

RED observed in this session:

```
uv run pytest -q tests/test_release_gate_check.py -k documented_verification
1 failed, 13 deselected
AssertionError: the documented sequence must not pass a coverage floor flag; it overrides pyproject.toml
```

GREEN after the documentation change:

```
uv run pytest -q tests/test_release_gate_check.py -k documented_verification
1 passed, 13 deselected
```

Both mutation directions observed in this session:

```
reintroduce --cov-fail-under=70 in the documented commands → FAILED (as required)
replace the coverage-floor paragraph with a pointer-free sentence → FAILED (as required)
restore the file → 1 passed
```

The test's assertion scope was corrected during this work unit, after the first version asserted
`pyproject.toml` inside the fenced code block while the guidance was placed in prose after it. The
final scope is: the flag against the commands, the owner against the section. The prose necessarily
names `--cov-fail-under` in order to forbid it, which is why the flag cannot be asserted against the
whole section.

Pinning test: `test_documented_verification_sequence_defers_the_coverage_floor_to_pyproject`.

## WU7 — artifacts

This directory: proposal, two capability deltas, spec index, design, tasks, this file, the verify
report, and `state.yaml`.

## WU8 — the final gate

Run over the finished tree, with the change artifacts present. All five checks passed:

```
uv run pytest -q                                    → 1897 passed, 0 failed, 63.57s
uv run pytest --cov -q                              → TOTAL 11332 947 91.64%
                                                      Required test coverage of 89.0% reached
                                                      1897 passed
uv run pyright src tests                            → 0 errors, 0 warnings, 0 informations
uv run ruff check .                                 → clean
uv run ruff format --check .                        → 310 files already formatted
uv run python scripts/release_gate_check.py --run   → exit 0, every non-audio gate PASS
```

Two things this run settles. The collected count is 1897, one more than the 1896 measured at
`234d6f5`, which is exactly the guard test WU6 added — so the "1897 after WU6" prediction in
`verify-report.md` is now measured rather than inferred. And coverage is unchanged at 91.64%,
so the new test adds coverage without moving the aggregate.

`uv publish` was not run and no release was published: publication authority is not exercised
by this change.
