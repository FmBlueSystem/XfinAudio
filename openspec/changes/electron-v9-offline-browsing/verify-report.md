# Verification evidence

2026-10-01, V9 working tree. This is a bounded implementation verification, not a release certificate.

## Focused checks
- `test_headless_offline_browsing.py`: 7 passed using the existing minimal Qt-free venv, with the test copied into an isolated directory to avoid the repository-wide Qt conftest. This positively verifies the feature imports and executes without PySide6.
- Targeted pyright (explicit minimal venv python path): 0 errors/warnings.
- Targeted ruff check and format check: pass.
- `npm run build`: strict main/renderer TypeScript pass.
- `offline-host.test.mjs`: 5 pass; exact native preview/commit, cancel and closing block commit, busy serialization, drain, IDs and nested validation.
- `offline-browse.test.mjs`: 6 pass; interpreted/manual values, stale response rejection, search/comparison/removal/recovery, cancel, busy and dirty-draft protection.
- `renderer.offline-app.test.mjs`: 2 pass; controls reachable in the real app and Prep retains the full Library, saved removal/recovery reachable without AI.
- `offline.integration.test.mjs`: 1 pass using the real Qt-free backend process, original domain methods, synthetic checked-in music, restart recovery and source SHA-256 invariance.
- Shared `restored-wiring.test.mjs` offline case: pass. No raw backend method, source path or renderer-supplied confirmation accepted by the public IPC.

## Requirement mapping
- R1/R2: Python interpreted/manual/invalid/missing-value, display-only numeric sort and original conservative duplicate representative tests; source count unchanged.
- R3: original local search/compare results and known-metadata counts; distinct 2–200 identity validation.
- R4: native host tests and Python exact-snapshot invalidation; changed names fail safely, absent confirmation fails, replay fails.
- R5: atomic archive failure trigger leaves original unchanged; restart lists recovery; restore preserves order, repeats and missing references; repeated restore cannot duplicate; original fixture audio hashes unchanged.
- R6: private paths absent from public DTOs; nested unknown fields rejected; safe errors, route/source generation and busy guards; no provider facade required.

## Global gate status
Final combined release gates follow the completed V9 integration. A diagnostic whole-Node run at 19:03 UTC had 330 passing and 4 failing: profile integration used the older no-librosa test interpreter, and three review/Prep integration tests were in their concurrently authored RED stage. None were this slice's tests. Do not present that snapshot as a green release gate. Full Qt suite/release_gate_check remains to be recorded against the final combined tree.
