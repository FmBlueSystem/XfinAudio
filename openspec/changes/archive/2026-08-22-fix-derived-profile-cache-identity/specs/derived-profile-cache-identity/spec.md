# Derived Profile Cache Identity Specification

## Purpose

Define cache-coherency behavior for the spectral, danceability, and edge-spectral derived profiles that share one persisted audio-file identity.

## Requirements

### Requirement: All derived-profile updates enforce shared identity coherence

Each derived-profile updater MUST compare the current audio-file identity with the identity associated with the cached profiles as part of the same persistence operation. The invariant MUST apply equally to spectral, danceability, and edge-spectral updates.

#### Scenario: Spectral update observes a changed file identity

- GIVEN cached spectral, danceability, and edge-spectral profiles belong to identity A
- WHEN the spectral profile is persisted for identity B
- THEN the new spectral profile is stored for identity B and both sibling profiles are invalidated

#### Scenario: Danceability update observes a changed file identity

- GIVEN cached spectral, danceability, and edge-spectral profiles belong to identity A
- WHEN the danceability profile is persisted for identity B
- THEN the new danceability profile is stored for identity B and both sibling profiles are invalidated

#### Scenario: Edge-spectral update observes a changed file identity

- GIVEN cached spectral, danceability, and edge-spectral profiles belong to identity A
- WHEN the edge-spectral profile is persisted for identity B
- THEN the new edge-spectral profile is stored for identity B and both sibling profiles are invalidated

### Requirement: Identity mismatch invalidates siblings while identity match preserves them

A derived-profile update MUST invalidate both sibling profiles when the stored identity differs from the current identity. When the identities match, the update MUST retain both sibling profiles unchanged. The identity and requested profile update MUST be committed as one coherent persistence result.

#### Scenario: A mismatched identity clears both siblings

- GIVEN both sibling profiles are present and their stored identity differs from the current file identity
- WHEN any one of the three derived-profile updaters persists its profile
- THEN both sibling profile values are absent or invalidated and the stored identity becomes the current identity

#### Scenario: An unchanged identity retains both siblings

- GIVEN both sibling profiles are present and their stored identity equals the current file identity
- WHEN any one of the three derived-profile updaters persists its profile
- THEN both sibling profile values remain unchanged and the stored identity remains current

### Requirement: The change remains within derived-profile cache persistence scope

The implementation MUST NOT change loudness analysis, audio data, DSP or profile algorithms, database schema, or profile serialization. Existing columns, identities, and transaction semantics remain the observable persistence contract.

#### Scenario: Updating a derived profile does not expand scope

- GIVEN a valid request to persist one derived profile
- WHEN the update completes
- THEN only the requested derived profile, its shared identity, and any required sibling invalidations differ
- AND no loudness result, schema definition, audio file, algorithm output, or serialization format is changed
