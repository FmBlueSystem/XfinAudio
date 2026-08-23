# Design: Fix Derived-Profile Cache Identity

## Technical Approach

Keep the existing shared identity (`file_mtime_ns`, `file_size_bytes`) and the three public update methods. Each method will stat the path once, serialize its requested profile, and execute one SQLite `UPDATE`. The statement always writes the requested profile, preserves each sibling only when both stored identity fields equal the captured stat, otherwise clears both siblings, and finally writes the captured identity. This implements the proposal without schema, serialization, worker, or loudness changes.

## Architecture Decisions

| Decision | Alternatives considered | Rationale |
|---|---|---|
| Compare the stored row identity inside each existing `UPDATE` | Read first in Python; add per-profile identities | A read-then-write sequence introduces a race and more round trips. Existing shared columns already express the intended identity and require no migration. |
| Treat identity as matching only when both non-null captured stat values equal the stored values | SQLite null-safe `IS`; preserve siblings when stat fails | A failed stat cannot prove identity. Fail-closed invalidation prevents unknown siblings from being accepted after the update. |
| Keep three explicit statements with the same invariant | Dynamic SQL helper for profile column names | SQLite cannot bind identifiers. Explicit statements avoid identifier interpolation and keep serializers and return behavior unchanged; parameterized tests enforce parity. |
| Update requested profile, siblings, and identity in one statement | Separate sibling-clear and profile-write statements | One statement is atomic under SQLite and evaluates sibling `CASE` expressions against the pre-update row, so no concurrent observer can see a new identity paired with stale siblings. |

## Data Flow

```text
update_*_profile(path, profile)
    -> capture Path(path).stat() as (mtime_ns, size_bytes), or (None, None)
    -> serialize requested profile
    -> one UPDATE of the matching row
         requested column = serialized profile
         sibling A/B = stored value iff stored mtime+size match captured stat; else NULL
         shared identity = captured mtime+size
    -> commit on context exit -> return rowcount > 0
```

If `stat()` raises `OSError`, both captured identity values remain `NULL`. The match predicate must require non-null captured values before equality checks; therefore both siblings are cleared even if the stored identity is also null. The requested profile is still stored, preserving current method behavior, but cache loaders exclude it until a later update records a complete identity.

## File Changes

| File | Action | Description |
|---|---|---|
| `src/xfinaudio/library/track_repository.py` | Modify | Add identity-guarded sibling `CASE` assignments to all three profile update statements. Keep `SCHEMA_VERSION = 4`. |
| `tests/test_track_repository.py` | Modify | Add strict-TDD coverage for matched, mismatched, and unavailable identity across all three updater families. |

## Interfaces / Contracts

Public method signatures and boolean return semantics remain unchanged. For each updater:

- the requested profile is written when `path` exists in the database;
- siblings are preserved only when captured mtime and size are both present and equal the stored values;
- a mismatch in either field, or unavailable stat, clears both siblings;
- requested profile, sibling disposition, and shared identity change atomically;
- a missing database row returns `False` and changes nothing.

No database columns, schema version, serialized profile shape, or cache-load interface changes.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Repository integration (RED) | Changed identity invalidates both siblings for spectral, danceability, and edge updaters | Parameterize updater family; seed all profiles, change size or mtime, invoke one updater, assert requested profile survives and both siblings are `None`. Cover each identity field as independently invalidating. |
| Repository integration (RED) | Matching identity preserves both siblings | Parameterize updater family; seed all profiles without changing the file, invoke updater, assert all three profiles remain. |
| Repository integration (RED) | Missing stat fails closed | Seed a row and all profiles for a real path, remove the file, invoke each updater, assert requested profile is written, siblings are cleared, identity columns are null, and profile cache loaders do not expose the row. |
| Regression | Existing rowcount and cache behavior | Retain current missing-row tests and run focused repository tests before the full project verification sequence. |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary.

## Migration / Rollout

No migration or schema bump is required. Existing profile rows remain untouched until an updater runs; invalidated profiles can be recomputed by existing workers. Rollback is a code/test revert.

## Open Questions

None.
