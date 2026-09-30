# Audit security boundaries

## Intent and scope
Address S1 (AI credential transport) and S2 (spreadsheet formulas in CSV) from the
2026-09-30 audit. Preserve supported HTTPS custom providers, ordinary CSV values,
numeric fields, and lossless JSON metadata. Correct loudness safety disclosure
without changing the owner's accepted automatic analysis/comment replacement.

Only Serato is used by the owner. S3 and all other-DJ-software-specific exporters,
containment, tests, and labels are explicitly out of scope. No real audio, user
data, credentials, live Serato writes, DSP changes, dependencies, or publication.

## Delivery / review budget
Explicit chained-PR plan (local commits only; no PRs are opened here):
1. `fix/security-ai-transport`: HTTPS validation, reject every redirect, non-forwarded
   credentials, offline regression tests, initial SDD artifacts (target <400 lines).
2. `fix/security-csv-text` based on slice 1: shared text-cell escaping for all shared
   CSV reports including Serato readiness, JSON preservation tests (target <400 lines).
3. `docs/security-loudness` based on slice 2: accurate English/Spanish loudness
   disclosure, remaining verification artifacts (target <400 lines).

## Risks, rollback, success
A provider requiring redirects must be configured with its final HTTPS endpoint.
Formula-like CSV text gains a leading apostrophe; JSON remains the raw interchange
format. Spreadsheet import behavior varies, so documentation must not claim a
particular spreadsheet was tested. Revert the corresponding local slice if needed.
Success means synthetic offline regressions and the integrated release gate pass.
