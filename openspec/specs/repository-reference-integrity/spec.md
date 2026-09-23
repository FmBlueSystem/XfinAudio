# Repository Reference Integrity Specification

## Purpose

Define the integrity contract for repository references: no operational file names another
machine-local checkout of this repository, and no documented procedure restates a value that
another file owns.

## Requirements

### Requirement: no operational file names another local checkout

No tracked file outside the historical record SHALL name a machine-local path belonging to a
different checkout of this repository. The project root SHALL be expressed relative to the
repository, and any procedure that needs the root SHALL resolve it with
`git rev-parse --show-toplevel`.

#### Scenario: a project root is repository-relative
- **WHEN** `openspec/config.yaml` is read
- **THEN** `project.root` is a repository-relative value, never an absolute machine-local path

#### Scenario: a new pointer cannot be added quietly
- **GIVEN** a tracked file outside `openspec/changes/` and `docs/reviews/` that names another
  local checkout path
- **WHEN** the guard runs
- **THEN** it fails and names that file

#### Scenario: the historical record is exempt
- **GIVEN** an archived change record or a review document that cites an old checkout
- **WHEN** the guard runs
- **THEN** the file is allowed, because it records what happened rather than instructing a reader

#### Scenario: referenced artifacts exist
- **WHEN** `openspec/config.yaml` names a change artifact
- **THEN** that path exists in the repository

### Requirement: documentation does not restate an owned value

A documented procedure SHALL NOT restate a value that another file owns. The coverage floor is
owned by `pyproject.toml`; the verification sequence in `AGENTS.md` SHALL therefore name the
owner and SHALL NOT pass a floor flag of its own.

#### Scenario: the documented sequence defers to the owner
- **WHEN** the verification sequence in `AGENTS.md` is read
- **THEN** its commands pass no coverage floor flag, and the section names `pyproject.toml` as
  where the floor lives

#### Scenario: the guard fails in both directions
- **WHEN** a floor flag is reintroduced among the documented commands
- **THEN** the guard fails
- **AND WHEN** the pointer to `pyproject.toml` is removed from that section
- **THEN** the guard fails
