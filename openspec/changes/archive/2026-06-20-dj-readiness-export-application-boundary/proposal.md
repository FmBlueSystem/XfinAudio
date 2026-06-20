# DJ Readiness Export Application Boundary

Move DJ Readiness report file writing behind the application layer so desktop export adapters do not call quality persistence helpers directly.

In scope: application write boundary, desktop delegation in `export_actions` and `export_coordinator`, focused tests and SDD evidence.
Out of scope: changing report schema/content, export formats, DSP/audio mutation, live Serato DB V2 writes.

Success: desktop no longer imports `write_dj_readiness_report` from `xfinaudio.quality.dj_readiness`; behavior and path derivation remain unchanged.
