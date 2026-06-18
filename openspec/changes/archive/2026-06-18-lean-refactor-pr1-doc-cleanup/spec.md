# Spec: Documentation cleanup

## ADDED Requirements

### Requirement: Stray root scratch document must be removed

`Integración con la función Prepare de Serato Dj .md` is a scratch note that duplicates
information already present in `docs/serato-compatibility-matrix.md` and
`docs/serato-fixture-compatibility.md`. It SHALL be deleted.

#### Scenario: No scratch root file

- **WHEN** the repository root is listed
- **THEN** no file with a non-ASCII filename remains in the root, except as listed in
  `.gitignore`.

### Requirement: Internal planning directory must be removed

The `.planning/codebase/` directory is internal tooling documentation and SHALL be
deleted. The three call sites (`AGENTS.md`, `openspec/config.yaml`,
`.atl/skills/gentle-ai-sdd-tdd/SKILL.md`) MUST be updated to drop the reference.

#### Scenario: No internal planning tree

- **WHEN** `git ls-files .planning` is invoked
- **THEN** it returns no entries.

### Requirement: Completed planning scratchpads must be removed

The `docs/plans/` directory contains dated planning scratchpads superseded by
`openspec/changes/` entries. They SHALL be removed. The single call site
(`docs/IMPLEMENTATION_HANDOFF.md`) MUST be updated to drop the reference.

#### Scenario: No stale plan files

- **WHEN** `git ls-files docs/plans` is invoked
- **THEN** it returns no entries.

### Requirement: Speculative recommendations must be removed

`docs/recommendations/next-evolution.md` documents a speculative direction without an
owner or implementation plan. It SHALL be removed.

#### Scenario: No speculative recommendations

- **WHEN** the `docs/recommendations/` directory is listed
- **THEN** it does not exist or is empty.

### Requirement: Harmonic mixing guide must move under docs/

`HARMONIC_MIXING.md` is a public-facing guide referenced by `README.md` and protected by
two tests. To consolidate documentation under `docs/`, the file SHALL be moved to
`docs/harmonic-mixing.md`. The README link, the public open-source docs test, the
harmonic mixing doc test, and `scripts/source_package_hygiene_check.py` MUST all be
updated to point at the new path. The 11 required content fragments and 5 forbidden
fragments asserted by the test MUST continue to hold in the new file.

#### Scenario: New path serves the same content contract

- **WHEN** `tests/test_harmonic_mixing_doc.py` runs
- **THEN** it reads `docs/harmonic-mixing.md` and every required and forbidden fragment
  assertion passes.
- **WHEN** `tests/test_public_open_source_docs.py` runs
- **THEN** the README link target is `docs/harmonic-mixing.md` and the link is preserved
  in both English and Spanish README sections.
- **WHEN** `scripts/source_package_hygiene_check.py` runs
- **THEN** `docs/harmonic-mixing.md` is in the required-files list and
  `HARMONIC_MIXING.md` is not.

### Requirement: Untracked tooling notes must be removed

`PI_CLAUDE_BRIDGE_OPUS_4_8.md` is untracked tooling notes already covered by
`.gitignore`. It SHALL be deleted from the working tree.

#### Scenario: No untracked tooling file

- **WHEN** the repository root is listed
- **THEN** `PI_CLAUDE_BRIDGE_OPUS_4_8.md` is not present.

## MODIFIED Requirements

None.

## REMOVED Requirements

None.

## Invariants

- The `openspec/` directory and all `openspec/changes/` content MUST remain intact.
- `README.md`, `LICENSE`, `NOTICE.md`, `CONTRIBUTING.md`, `AGENTS.md`, `SECURITY.md`
  MUST remain available.
- The two harmonic mixing tests MUST pass against the new path without changing their
  required/forbidden fragment list.
- Source code, tests, and `pyproject.toml` MUST NOT be touched (other than the
  documented path renames).
