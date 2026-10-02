# Requirements

- Default release behavior stays unchanged unless the explicit batch-size option is present
- Collect the complete configured suite into structured evidence; empty/failed/duplicate collection fails
- Keep test files whole and preserve their collection order; batch size is a target, not a reason to drop tests or split shared module fixtures
- Every batch verifies its exact collected node IDs against the original manifest; missing/extra tests, failed tests, interrupted commands, missing coverage or source changes fail closed
- Coverage data belongs to a fresh isolated run directory, never mixed with previous runs; only after all batches pass, combine and report with the project's existing configured floor
- No coverage-floor command-line override, deselection, automatic retry or newly introduced skip
- Evidence records commands, collection, batches and outcomes; aggregate report preserves failure propagation and remains separate from manual release gates
