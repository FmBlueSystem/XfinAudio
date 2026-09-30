# Verification

## Focused requirements
- R1: atomic-save RED injected fsync and replace failures (2 failures before Apply); GREEN original complete settings survive, temporary files removed when cleanup is permitted. Base repository suite: 10 passed.
- R2/R3: invalid JSON/shape/future-schema/encoding bytes preserved in unique recovery files; startup displays preserved path and Settings guidance. Preservation failure leaves original bytes. Dialog and spectral-slider save failures retain active settings and warn. RED 8 failures; GREEN 21 passed.
- R4/R5/R6: delete cascades child rows; invalid parents rejected; idempotent legacy orphan cleanup preserves valid ordering; both repositories close operation-local connections after success/error. RED 4 failures; GREEN 133 repository tests.
- Independent original audit probe after fixes: 0 orphan child rows, empty foreign_key_check, 100 reads with GC disabled -> 0 extra file descriptors (original +100).
- R7/R8: independent review found automatic write-back risk during corrupt-settings recovery and cleanup masking. RED 7 failures; GREEN recovery-only loudness disabled, visible paused-write warning, typed primary error survives cleanup denial. Combined settings suites: 23 passed.
- Focused Pyright on settings, controller, both repositories, shared connection factory and new tests: 0 errors. Ruff checks/format pass.

Logs: `/workspace/shared/xfinaudio-audit/settings-{atomic,recovery,safety}-{red,green}.log`, `sqlite-{red,green}.log`, `sqlite-repro-fixed.log`.

## Integrated verification
Pending completion of the related lifecycle, UI and musical-algorithm slices and the full configured release gate on the final integrated commit.

## Safety and limits
Only isolated temporary settings/SQLite/synthetic records used; no user music or Serato database writes. Normal default-enabled loudness and explicit enabled policy are preserved; only invalid-settings recovery pauses destructive write-back. Atomic replacement/fsync failures are injected; no physical power-loss or disk-full simulation, native macOS run, or filesystem-specific durability certification is claimed. Undeletable temporary files can remain when cleanup itself is denied, without masking the typed save error or replacing valid settings.
