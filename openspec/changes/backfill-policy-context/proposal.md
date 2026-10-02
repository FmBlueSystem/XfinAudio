# Public backfill policy
Direct slot replacement bypasses the original hard strategy filters. Preserve
resolved generation policy so callers cannot accidentally admit E10 into an E5
same-energy set. Scope: immutable policy metadata, helper, desktop seam, tests.
No audio/Serato writes, dependencies, optimizer or genre fallback changes.
Rollback: revert this change. Success: pure and desktop regression suites pass.
If the review budget exceeds 400 lines, chain metadata capture and enforcement
as separate <=400-line commits; integrated gate belongs to the integration owner.
