# Verification

20 focused tests pass; Ruff lint/format pass. RED logs and full native dependency reports are in the handoff evidence. Direct appdata cache, frozen executable hash and hostile/alias failures covered. Relocated empty-PATH frozen probe succeeds cold/warm across six tagged formats with read-only HOME/bundle and source bundle hidden; warm .nbc data loads observed. All 223 frozen native objects and 13 Electron native objects resolve to contained/system dependencies; 19-file trusted FFmpeg closure relocalized. All synthetic source hashes/mtimes and original/copy baselines conserved. Complete aggregate, final application freeze, actual packaged native player, human/audible acceptance and Developer ID/notarization are not asserted. Owner runs V11 full gates; no engine/Electron/shared Linux changes.

## Integrated packaging review

A new regression first failed against the missing post-signing manifest operation.
The corrected builder explicitly labels embedded inventories pre-final-signing,
then signs, verifies, audits actual delivered native bytes and writes a sibling
manifest outside the signed app. It retains exact-source gate and input rechecks.

The cache regression also runs against the legacy aggregate's Numba 0.65.1 and
the locked Qt-free Numba 0.68.0. It proves inheritance of each original stamp,
changed-executable invalidation and explicit SHA256 equality for content-hash
stamps. The supplied actual native frozen probe separately requires executable
SHA256 equality under the pinned production runtime. No application behavior or
original V10 source file changed. Full final-source gates and native application
acceptance remain distinct from these focused and dependency-only checks.

## Native V11 finding and V12 regression

Native V11 signed successfully and its frozen core completed real six-format
analysis, cache, isolation and persistence tests; its GUI was not accepted because
the stock main executable name caused development-mode core selection. V12 changes
only builder identity, matching native-audit paths, tests and documentation. Two
regressions were first observed failing; original/relocated packaged-mode and final
GUI/media validation must be repeated natively on the newly gated exact source.
