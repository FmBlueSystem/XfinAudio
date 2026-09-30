# Apply progress
2026-09-30: Proposal, specification, design and tasks initialized before production changes. Chained review budget: each commit <=400 changed lines. RED privacy tests next.

Slice 1: RED reproduced missing privacy module, then GREEN 45 focused tests including the original path-in-title/genre disclosure bug and generic quoted POSIX/Windows paths. Additional Windows intent regression passes (46 combined tests). No live requests.

Slice 2: RED missing structured service, GREEN 35 new Library/Editor contracts and 81 combined focused tests. Shared parser rejects extra fields, duplicate keys, nonfinite/oversized/fenced JSON and invalid numbers; errors are bounded. Library validates existing genres and filters; Editor emits only four canonical local commands. Refactored shared transport/JSON utilities for subsequent saved/evidence services.

Slice 3: RED missing saved-set exports, GREEN 11 anonymous descriptor/selection tests. Coverage counts preserve missing measurements, named requests map locally to index IDs in a single pass, duplicate names require clarification, and model IDs/actions/fields are whitelisted. Focused typing passes using the shared interpreter.

Slice 4 approved extension: RED missing evidence commentary entrypoint, GREEN 18 Metadata/Live tests. Input schemas reject paths/titles/extra fields, nonfinite scores, impossible gap counts and unready or reordered candidates. Output is bounded, plain, read-only commentary with validated fact IDs. Narrative semantics remain optional model interpretation, not authoritative measurements; UI must keep that label and local facts visible.
