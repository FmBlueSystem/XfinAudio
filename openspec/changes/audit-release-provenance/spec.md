# Requirements

## R1 Exact clean source gate
GIVEN a missing repository, dirty tracked/staged/untracked source, failed gate,
or a changed commit/source during gate/build, WHEN packaging is requested,
THEN fail closed and do not proceed to the next packaging stage.
GIVEN clean source, WHEN building or reusing an app, THEN execute the non-audio
release gate for that exact source before building, executing, or packaging it.

## R2 Bundle provenance and integrity
GIVEN successful gate/build/smoke, WHEN recording provenance, THEN record source
SHA, project version, gate command, and deterministic bundle-content digest.
GIVEN absent/malformed evidence, wrong commit/version, modified/additional/missing
files, changed executable permissions or unsafe symlinks, WHEN reusing an app,
THEN refuse before bundle execution or signing.
GIVEN unchanged content and matching source/evidence, WHEN reusing and staging,
THEN permit packaging only after the staged copy matches the verified bundle.

## R3 Supply-chain clarity
GIVEN checked-in release workflows, WHEN external actions are referenced,
THEN each reference is a full reviewed official commit SHA with version comment.
GIVEN FFmpeg building, WHEN downloading sources, THEN download only the
hash-verified archive and never imply verification of an unused signature.
Checksum mismatch still prevents extraction and compiler execution.

## R4 Compatibility and boundaries
GIVEN optional signing or notarization settings, WHEN packaging proceeds,
THEN preserve the existing credential gates and failure propagation.
Tests use temporary repositories, bundles, and synthetic tools only; no real
packaging, signing, notary service, live data, or publication is exercised.
