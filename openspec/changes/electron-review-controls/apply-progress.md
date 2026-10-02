# Apply progress
SDD complete. RED tests next.

RED (2026-10-01 18:53 UTC): all nine new backend tests failed against absent commands/accessors under the original verification environment. Minimal Qt-free venv cannot run root conftest (expected PySide6 dependency); use original combined verification environment for pytest, isolated subprocess for Qt-free assertions.
GREEN implementation in dedicated review_evidence/generated_review/prep_settings modules; shared backend hooks handed to composition owner.

Renderer RED→GREEN: missing module tests, actual app composition failures, lifecycle regressions for dirty edits before first load and stale async library responses. Added generated-review/prep-settings controllers and views with explicit save/restore/discard, unavailable-control warning/clear choice, global busy/dirty state, safe inline evidence and exact current-ID mutations. Dedicated main security validator rejects raw paths, extra/missing fields, duplicate/conflicting IDs. Shared composition delivered by UI owner.

Safety RED→GREEN: changed source during replacement assessment formerly published a partial edit; all proposed source identities now revalidate before mutation. Cached prep.select could formerly launder stale generation source/policy into a new review identity; generation-time plan snapshot now precedes engine work and is checked before publication and every later selection, while reviews retain its original binding. Four targeted stale-plan failures reproduced then passed.

No pushes/releases. All source-file mutations in tests use disposable synthetic or copied fixture files. Temporary verification moved to workspace storage; no native Mac operations.
