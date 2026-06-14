# Spec: Manual QA Checklist Document

## Goal

Provide a human checklist and placeholder for manual Mixed In Key QA evidence.

## Acceptance Criteria

- `docs/qa-manual-mik-evidence.md` exists.
- It documents:
  - Required MIK folder characteristics (at least 5 complete tracks, some incomplete).
  - Commands to run the harness.
  - Expected outcomes for scan, recommend, review, and export.
  - A section where the maintainer pastes the generated evidence.
- `release_gate_check.py` checks for the existence of this file to decide if the manual gate is completed.
