# Design
Serialize settings fully before opening a same-directory NamedTemporaryFile. Flush/fsync and os.replace commit atomically; finally removes abandoned temporary files. Preserve permissions where feasible and never expose credentials (settings have none).
Keep strict load() compatible. Add explicit load_with_recovery() for desktop startup, quarantine only invalid content using unique sibling filenames, expose a recovery diagnostic. Read/access failures remain errors; preserve unsupported versions before defaults.
SettingsController saves before publishing state; typed persistence failures produce a warning.
Use an operation-local shared context-managed SQLite factory with row factory, FK enforcement, transaction commit/rollback and unconditional close. Convert both repositories; VACUUM remains outside a write transaction. Add idempotent named playlist integrity migration, scoped to orphan children.
Use synthetic temp data and offscreen widgets. No real user data, audio or Serato mutations.
