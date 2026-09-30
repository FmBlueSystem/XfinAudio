# Apply progress

- 2026-09-30: Read repository governance; proposal, specification, design and task gates complete. Production work has not started. Tests use synthetic credentials and injected transports only.
- Runtime slice RED: new tests failed collection for missing runtime_settings. GREEN: 92 focused runtime/adapter/settings tests passed. Runtime saves replace only non-secret switches; per-call probe consent never changes ambient enablement.
- Probe slice RED: missing connection_test module. GREEN: 13 runtime/probe tests passed, with disabled/missing, invalid endpoint/file, authentication, offline, timeout, malformed response, safe errors and retry. Every transport is synthetic; no operator credential file was read.
- Worker lifecycle slice RED: missing ai_connection_probe module. GREEN: four lifecycle tests passed (non-blocking, duplicate suppression, logical cancellation/stale result, retry, safe unexpected error, destroyed owner). Cancel cannot recall an already sent request; a second send waits for the bounded prior request to finish.
- Controls slice RED: missing ai_settings_panel module. GREEN: nine panel/lifecycle tests passed. Controls disclose destination and exact probe text, never expose a key field, and inspect file presence without reading its contents. Toggling only changes an immutable candidate.
