# Apply progress

Planning phases complete before production edits. Strict RED/GREEN evidence follows per slice.

## Atomic save slice
- RED: two fsync/replace failure injections failed before production edit (settings-atomic-red.log).
- GREEN/REFACTOR: same-directory temporary write, flush/fsync, atomic replacement and finally cleanup; 10 focused tests pass.

## Explicit recovery and UI slice
- RED: eight regression cases failed before Apply (settings-recovery-red.log).
- GREEN/REFACTOR: preserve invalid JSON/encoding/schema bytes in unique sibling backup; strict read errors remain typed; visible startup diagnostic. Settings UI saves before publishing and keeps prior state on failure.
- VERIFY: settings repository, recovery UI and settings controller: 21 passed (settings-recovery-green.log).

## SQLite ownership/integrity slice
- RED: 4 failures proved missing cascade, legacy orphan cleanup and deterministic close for both repositories (sqlite-red.log).
- GREEN/REFACTOR: operation-local shared connection context manager enables foreign keys, commits/rolls back and always closes; idempotent startup migration removes only orphan playlist references. VACUUM remains outside an active transaction.
- VERIFY: 133 playlist/track/connection tests pass (sqlite-green.log); tracked handles are closed after 20 reads per repository even when references remain alive, plus error path.

## Independent-review recovery safety
- RED: seven failures demonstrated cleanup masking and recovery default enabling write-back (settings-safety-red.log).
- GREEN: recovery-only loudness disabled, warning explicit; normal fresh default remains enabled. Cleanup failures cannot mask typed errors. 23 focused tests pass (settings-safety-green.log).
