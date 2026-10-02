# Verification

## Final integrated verification — 2026-09-30
All automated gates passed at code-complete commit `9e7c894dcbe482ea1b6d6f02c9c9ca05a30c53b0`: **2921 tests**, **93.54% coverage**, clean types/lint/format, smoke, publication/source-package hygiene and PyInstaller check-only. Command: `uv run python scripts/release_gate_check.py --run`. Coverage floor remains 89% in pyproject.toml.

This supersedes earlier isolated-run pending/blocker notes below. Documentation-only closure commits are rerun through the same gate before delivery; final exact-SHA evidence accompanies the delivery. Native macOS, real music/listening, and live Serato import remain unverified. No push, merge, release, or deployment.


Focused verification complete. Only synthetic/offline fixtures were used. The integrated
release gate will be run by the parent after all review slices are combined.

## R1/R2: transport (focused pass)
`python -m pytest tests/test_nan_client.py tests/test_nan_transport_security.py -q`
passed 95 tests. RED was 26 failed / 10 passed in the new module before production.
Coverage includes direct HTTP/malformed/credential-bearing URLs, same-host redirects,
other origins, changed ports, HTTP downgrade, 301/302/303/307/308, and non-redirect
success. Intercepted HTTPS/HTTP handlers return in-memory data; no socket is used.

`python -m pyright --pythonpath <shared-venv>/bin/python` for the two changed Python
files: 0 errors. Focused `ruff check` and `ruff format --check` pass after formatting.
Integrated gate pending; subsequent slices are recorded below.

## R3/R4: CSV and JSON (focused pass)
`python -m pytest tests/test_csv_security.py tests/test_metadata_gaps.py
 tests/test_playlist_exporters.py tests/test_dj_readiness.py
 tests/test_application_dj_readiness_export.py -q` passed 78 tests.
RED was 32 failures / 8 passes in the new module before production changes.
All three shared CSV writers are covered for =/+/−/@ (ASCII minus in tests),
space/tab/CR/LF/NUL/NBSP/BOM prefixes, ordinary text, quotes, commas, and multiline
cells. Tests confirm the exact raw JSON strings and unchanged numeric columns,
including negative numbers. Focused pyright: 0 errors; lint/format: pass.

No spreadsheet UI was available or used. Literal-cell behavior is validated at the
serialized boundary; documentation requires text import and discloses this limit.
The integrated release gate remains pending with the parent.

## R5: truthful loudness disclosure (focused pass)
`python -m pytest tests/test_public_open_source_docs.py tests/test_harmonic_mixing_doc.py -q`
passed 9 tests; documentation RED was 2 failed / 5 passed before edits. Runtime
behavior is unchanged. Disclosures match enabled=True, automatic completion write-back,
ID3 COMM deletion, FLAC COMMENT / MP4 ©cmt replacement, and FLAC DESCRIPTION preservation.

## Remaining verification / excluded scope
Parent must run `uv run python scripts/release_gate_check.py --run` after integration.
No full-gate, macOS UI, real audio, spreadsheet UI, or live-provider certification
is claimed here. No push, PR, deployment, or real credential use occurred.
S3/non-Serato containment was deliberately excluded by the owner's narrowed scope.
