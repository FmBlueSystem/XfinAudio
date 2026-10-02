# Requirements

- The user chooses an explicit Serato destination through a native folder selector; renderer receives only an opaque destination ID and label
- Preview is read-only and bound to the exact source review or complete saved-set revision, source file identities, destination identity and immutable target/name/backup plan
- Missing tracks or hard readiness blockers prevent commit; needs_review remains eligible after explicit confirmation
- Source-volume identity stays distinct from output location; crate references resolve to all intended source tracks, with no silent dropping or invented metadata
- Commit revalidates the preview and preserves existing deterministic Serato bytes, backup, no-clobber publication and readback/rollback protections
- Changed sources/destinations, path traversal/symlinks, collisions or repeated requests cannot cause an unintended write; duplicate commit is idempotent or explicitly consumed
- No automatic live-folder discovery/write, audio modification or database V2 write; tests operate only disposable fake Serato roots
- User-facing errors hide transport wrappers/codes/private paths while retaining actionable Spanish guidance and internal machine codes
- Source archives exclude dependencies, caches, machine-specific symlinks and runtime files

- Export inputs are bounded to 500 track references and 16 MiB crate IO; oversized input fails without truncating a saved set or writing output
- Failed-readback removal must not delete a concurrent arrival at the public crate name; captured recovery files remain when restoration conflicts
