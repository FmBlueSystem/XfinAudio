# Apply progress

2026-10-01: Read AGENTS.md and gentle-ai-sdd-tdd. Inspected existing guidance, domain report, TrackRecord and desktop regression tests. Proposal/spec/design/tasks were written before test or production changes. Defined the report payload for integration. No production edits yet.

RED: Qt-free pytest --noconftest tests/test_metadata_guidance_headless.py produced 6 failures for missing core/helper imports and 1 expected Qt-adapter skip, before production edits. Captured at /tmp/metadata-guidance-red.log.

GREEN/REFACTOR: moved the existing algorithm into repair_guidance_core, added identity-default translation injection, and reduced the legacy module to a Qt adapter that reexports RepairPriority. Added the public report using the domain gap report and existing core guidance, with opaque IDs and Untitled fallback. Only owned files changed; no dependency installation, backend/renderer edits, provider access or audio/Serato writes.

VERIFY: Qt-free focused tests passed (6 plus 1 expected legacy skip); the Qt-enabled metadata regression group passed (43). Both explicit-interpreter type checks and scoped lint/format checks passed. The final combined release gate remains required.
