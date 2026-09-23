# Spec Delta: release-gate-integrity (NEW)

## ADDED Requirements

### Requirement: the publication gate inspects the publication tree

The publication-hygiene gate SHALL determine what would be published from the Git index
(`git ls-files`), not by walking the working tree, so that a git-ignored local artifact can never
fail the gate and a force-added forbidden file can never pass it.

#### Scenario: an ignored local artifact does not fail the gate
- **GIVEN** a git-ignored `.DS_Store` at the repository root
- **WHEN** the publication hygiene gate runs
- **THEN** it passes, because the index does not contain that file

#### Scenario: a forbidden file that is tracked still fails the gate
- **GIVEN** a private handoff file force-added to the index despite `.gitignore`
- **WHEN** the publication hygiene gate runs
- **THEN** it fails, because the index contains the file

### Requirement: the coverage floor has exactly one owner

The coverage floor SHALL be defined only in `pyproject.toml`
(`[tool.coverage.report] fail_under`). No command in the release gate or in the documented
verification sequence SHALL pass `--cov-fail-under`, because a command-line flag overrides the
configuration and makes the configured value decorative. The floor SHALL sit close enough to
measured coverage that a real collapse of the suite fails the gate.

#### Scenario: the gate command passes no floor flag
- **WHEN** the release gate's tests-and-coverage command is inspected
- **THEN** no argument begins with `--cov-fail-under`

#### Scenario: a floor far below measured coverage is refused
- **GIVEN** measured coverage of 91.64%
- **WHEN** `pyproject.toml` declares a floor below 85
- **THEN** a test fails, because such a floor cannot catch a regression

### Requirement: the source distribution carries no planning or review scratch

The source distribution SHALL exclude planning and review scratch — `PLAN*.md`, `SPEC-*.md`,
`docs/reviews/`, `docs/superpowers/` and `odd/` — and the publication inspection SHALL refuse
those paths if they appear in an archive anyway.

#### Scenario: the archive never contains the scratch
- **GIVEN** the sdist build configuration
- **WHEN** a path under `docs/reviews/` or a `PLAN*.md` file is considered
- **THEN** the build excludes it, and a test pins the exclusion so it cannot silently reverse

#### Scenario: detection is the second line of defence
- **GIVEN** an sdist archive that contains a planning or review document anyway
- **WHEN** the hygiene inspection reads the archive
- **THEN** it fails and names the offending member

### Requirement: the publication path is gated as strongly as the pull-request path

The publish workflow SHALL run the release gate before building, SHALL NOT invoke the test suite
separately from that gate, and SHALL refuse to publish when the Git tag disagrees with the version
in `pyproject.toml`.

#### Scenario: the release gate runs before publishing
- **WHEN** the steps of the publish workflow are inspected
- **THEN** the release gate is invoked, and it is invoked before the build and publish steps

#### Scenario: a drifting tag is refused
- **GIVEN** a tag whose name disagrees with the version in `pyproject.toml`
- **WHEN** the publish workflow reaches its version step
- **THEN** the step fails with an error naming both values, and nothing is published

#### Scenario: the suite is executed only through the gate
- **WHEN** the workflow's `run:` blocks are inspected
- **THEN** none of them invokes `pytest`, because the gate already executes the suite once
