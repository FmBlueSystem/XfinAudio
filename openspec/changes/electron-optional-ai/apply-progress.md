Starting offline-only implementation; no credentials or provider calls.

2026-10-01 corrective review:

- Recovered and reviewed all eight AI surfaces against their original adapters and the migration specification.
- RED: the existing startup and real safe-export provider firewalls failed because the backend eagerly imported OptionalAI. Two new lazy-initialization/invalidation tests also failed before production changes. GREEN: provider-free command constants plus a lazy facade and non-instantiating invalidation restore both original firewalls without weakening them.
- RED: a selected dummy file missing at lstat exposed its full path in the native rejection. Added missing/deleted/native-chooser-error regressions. GREEN: picker and filesystem exceptions become typed credential-unavailable errors without the original message or cause.
- RED: three start/end/both boundary tests and one hard-control test showed AI Apply replacing local choices. GREEN: original local-boundary precedence and required/excluded unions are restored; conflicting merged controls leave the form unchanged.
- Focused results: 239 Python tests passed; 46 AI Node tests passed with the real-core injected-transport integration enabled and zero skips. Strict TypeScript build passed. Changed Python files pass Ruff lint/format and targeted Pyright (0 errors).
- No real credentials were inspected and no provider network calls occurred. Test writes were confined to disposable fixtures/app profiles. Full aggregate and native macOS dummy-only acceptance remain pending with the coordinator.

Additional bounded corrective patch validated in an isolated source copy: six stale-cache regressions were RED, then GREEN with reference-scoped history; missing lock facts and original Prep/Review timeout tests were RED, then GREEN with truthful optional evidence and capped per-surface policy. Combined focused Python/domain targets passed 235 tests; native-host IPC policy target passed 7 tests; changed-file Ruff/type checks passed. No real provider calls or canonical edits were used while the prior aggregate was running. Integrate this patch before final whole-source gates/native handoff.
