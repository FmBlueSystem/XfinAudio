# Specification Index: harden-release-gates

This change carries two capability deltas. The normative text lives in the deltas, not here.

This file exists because `AGENTS.md` requires an active change to contain `spec.md`. It is an
index rather than a third copy of the requirements, because duplicating a requirement in two
files is the same defect as duplicating a coverage floor in two files.

| Capability | Delta | Status |
|---|---|---|
| `release-gate-integrity` | `specs/release-gate-integrity/spec.md` | new |
| `repository-reference-integrity` | `specs/repository-reference-integrity/spec.md` | new |

## Requirements at a glance

**release-gate-integrity** — the publication gate reads the index and not the filesystem; the
coverage floor has exactly one owner; the source distribution excludes planning and review
scratch; the publication path runs the release gate and refuses a mismatched tag.

**repository-reference-integrity** — no operational file names another local checkout; a
documented procedure does not restate a value that another file owns.

Scenarios for each requirement are in the deltas.
