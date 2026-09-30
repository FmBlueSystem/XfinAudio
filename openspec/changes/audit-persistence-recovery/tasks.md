# Tasks
1. RED settings write/fsync/replace failure tests; GREEN atomic replacement; REFACTOR cleanup; VERIFY focused repository tests.
2. RED invalid startup recovery and UI failure tests; GREEN explicit recovery/diagnostic and save-before-publish; REFACTOR; VERIFY focused desktop tests.
3. RED close ownership/cascade/orphan migration tests; GREEN connection factory and scoped migration; REFACTOR; VERIFY repository suite.
4. Integrate other audit branches; run uv run python scripts/release_gate_check.py --run using isolated HOME, offscreen Qt and audit cache. Record exact results without overriding configured coverage floor.
