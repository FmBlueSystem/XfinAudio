# Proposal: Fix Derived-Profile Cache Identity

## Intent

Prevent stale derived audio profiles from being treated as current after an audio file is replaced. The repository currently stores one shared file identity for spectral, danceability, and edge-spectral profiles; refreshing any one profile also refreshes that identity, which can incorrectly validate stale sibling profiles.

## Scope

### In Scope
- Keep the three derived-profile caches coherent with their shared file identity.
- Invalidate sibling profile JSON when a profile update observes a different file identity.
- Preserve sibling profiles when the stored and current identities match.
- Prove both paths with strict-TDD repository tests.

### Out of Scope
- Loudness analysis or any loudness module.
- Audio mutation, DSP changes, or profile algorithm changes.
- Database schema or profile serialization changes.
- Changes outside `TrackRepository` cache persistence and its focused tests.

## Capabilities

### New Capabilities
- `derived-profile-cache-identity`: Defines atomic cache-coherency behavior for spectral, danceability, and edge-spectral profiles that share one persisted file identity.

### Modified Capabilities
- None.

## Approach

Update each derived-profile persistence operation so one database statement compares the stored identity with the current file stat. On mismatch, it writes the requested profile and clears both sibling profile columns before storing the new shared identity. On match, it writes the requested profile while retaining the siblings. Reuse the existing columns and transaction behavior; add no migration.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/xfinaudio/library/track_repository.py` | Modified | Enforce identity-aware sibling invalidation in all three profile updates. |
| `tests/test_track_repository.py` | Modified | Cover mismatched-identity invalidation and matched-identity preservation. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Valid sibling profiles are cleared unnecessarily | Low | Compare both stored identity fields and test the identity-match path. |
| One updater behaves differently from the others | Medium | Apply and test the same invariant for all three profile families. |

## Rollback Plan

Revert the repository and test changes. No migration or stored-data rewrite is required; invalidated profiles can be recomputed by existing workers.

## Dependencies

- Existing SQLite schema and derived-profile completion workers.

## Success Criteria

- [ ] Updating any derived profile after file identity changes invalidates both stale siblings atomically.
- [ ] Updating a profile with unchanged identity preserves both sibling profiles.
- [ ] The focused repository tests and project verification suite pass.
