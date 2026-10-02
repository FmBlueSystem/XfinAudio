# Qt-free metadata guidance

Extract the existing deterministic read-only repair guidance into a neutral core and expose an opaque-identity metadata report for the Electron bridge. Preserve the Qt API, translation context, priority order, explanations, and bounded plan. Reuse the existing gap report; do not introduce metadata inference, audio/tag writes, DSP, providers, or live Serato access.

Success: neutral imports work without Qt; current desktop guidance tests pass; counts, year coverage, explanations and priorities match the existing domain contract; public tracks contain SHA256 identities rather than filesystem paths. Rollback: revert this isolated extraction and helper.

Review plan if combined artifacts exceed 400 changed lines: chain slice 1 (neutral guidance extraction, wrapper and core/compatibility tests) before slice 2 (report projection and report/firewall tests). Slice 1 consists of the core/wrapper plus core, legacy and import-firewall test sections (approximately 230 changed lines); slice 2 consists of the report projection, report tests and SDD artifacts (approximately 190 changed lines). Each slice stays below the 400-line budget; aggregate integration and release gates apply to the combined application. No push or release is included.
