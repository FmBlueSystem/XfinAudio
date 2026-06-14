# Serato Compatibility Matrix

XfinAudio exports Serato crates as deterministic fixture bytes. This matrix documents which Serato versions and workflows are covered by that validation, and which remain unverified.

## Compatibility matrix

| Serato version / workflow | Fixture byte validation | Live library import | Notes |
|---------------------------|-------------------------|---------------------|-------|
| Serato DJ Pro 2.x+ crate format (documented TLV subset) | Yes | Not verified | Validated against the deterministic crate bytes produced by `build_serato_crate_bytes`. Assumes the TLV subset is stable across these versions. |
| Serato DJ Pro 1.x or earlier | No | Not verified | Out of scope for the current fixture set. |
| Serato ScratchLive / older crate formats | No | Not verified | Legacy crate formats are out of scope. |
| Serato database V2 (`database V2`) files | No | Not verified | XfinAudio does not read, parse, or mutate live Serato database files. |
| Live `_Serato_/Subcrates` write | No (dry-run by default) | Not verified | Confirmed writes require explicit user confirmation and are not part of the release-candidate guarantees. |

## What "fixture validation" means

- `validate_serato_crate_bytes` checks that generated crate bytes parse as a valid TLV structure.
- It verifies the crate version string and the ordered `ptrk` track paths.
- It does not exercise a live Serato installation.

## What this does not prove

- Real-world import into Serato DJ Pro.
- Compatibility with every released Serato patch version.
- Behavior when the crate is copied to a live `_Serato_/Subcrates` folder on a DJ computer.

## Safety posture

- Crate planning remains dry-run by default.
- Confirmed writes require `confirm=True`, create a backup when replacing an existing crate, validate the written bytes against the planned artifact, and expose rollback guidance.
- Always back up your live Serato library before importing any generated crate.
