# Proposal: Library repository port boundary

## Intent

Make XfinAudio's library persistence contracts explicit so desktop and application code can depend on repository ports instead of concrete SQLite repository classes.

## Problem

The layered architecture map identifies `library` as a mixed package: domain models, persistence contracts, and concrete SQLite repositories live close together. Some consumers type directly against concrete repositories, which makes the next saved-playlist application service slice harder to test and review.

## Scope

In scope:

- Add explicit library repository port contracts.
- Make existing concrete repositories conform structurally without changing storage behavior.
- Replace desktop/application type dependencies on concrete repositories where a port is enough.
- Add tests that protect the boundary.

Out of scope:

- Database migrations or storage format changes.
- Moving saved-playlist orchestration into an application service.
- UI redesign.
- Serato, export format, audio mutation, or DSP behavior changes.

## Success criteria

- `PlaylistCoordinator` no longer imports `xfinaudio.library.playlist_repository`.
- `PlaylistWorkflowService` uses shared library repository ports instead of a local persistence protocol.
- Concrete SQLite repositories satisfy the new ports under type checking.
- Focused and full verification gates pass.

## Rollback plan

Revert the slice commit. Because the change is type/boundary-oriented and keeps concrete repository behavior unchanged, rollback does not require data migration.
