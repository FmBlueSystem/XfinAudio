# Requirements

1. Exact bounded opaque-ID worklists are validated against current authorized metadata and the chosen complete/incomplete/missing-field scope. Empty, duplicate, unknown, mismatched or over500 selections fail closed.
2. Preview is read-only and clearly labels a metadata worklist, never DJ readiness. Existing immutable source/destination identities and native confirmation apply.
3. Existing pure metadata planners create references; existing safe crate writer alone publishes, validates and backs up. Source audio and database V2 remain unchanged.
4. Changed metadata/files/destination invalidate preview; renderer supplies neither file paths nor confirmation authority.
5. Metadata search/field selection exports the exact filtered worklist across all pages, never silently truncates to a page.
