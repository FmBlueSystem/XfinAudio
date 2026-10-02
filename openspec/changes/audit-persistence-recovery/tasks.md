# Tasks
1. RED settings write/fsync/replace failure tests; GREEN atomic replacement; REFACTOR cleanup; VERIFY focused repository tests.
2. RED invalid startup recovery and UI failure tests; GREEN explicit recovery/diagnostic and save-before-publish; REFACTOR; VERIFY focused desktop tests.
3. RED close ownership/cascade/orphan migration tests; GREEN connection factory and scoped migration; REFACTOR; VERIFY repository suite.
4. Integrate other audit branches; run uv run python scripts/release_gate_check.py --run using isolated HOME, offscreen Qt and audit cache. Record exact results without overriding configured coverage floor.
5. RED cleanup-masking and recovery write-back-policy tests; GREEN best-effort cleanup and recovery-only disabled loudness; REFACTOR warning; VERIFY persistence/desktop focused suite.

Integrated verification completed on 2026-09-30 at `9e7c894`: all automated release gates passed, 2921 tests and 93.54% coverage. Native validation remains separate.
