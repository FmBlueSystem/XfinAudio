# Verification

Keep 4,056 collected, 4,035 passed and 21 skipped as the prior hosted observation; any corrected hosted result requires a fresh run and its own exact source identity.

- FFmpeg prerequisite: a regression requires the existing public install/probe step in each hosted job before test execution. It failed for the legacy job before the workflow change and now passes for both jobs.
- Complete execution: real disposable pytest subprocesses previously accepted setup and call skips. Both now stop the first batch with status 1, an empty executed-call list and no combined coverage report.
- Existing semantics: successful calls retain exact manifest evidence; assertion failures retain status 1 and their executed call identity. Collection drift, suppressed execution, source drift, invalid coverage and configured-floor regressions still pass.
- Strict RED: 3 failed, 1 passed. Initial focused GREEN: 52 passed. Expanded final verification: 61 passed (test_sharded_coverage_gate, test_electron_ci_gate, test_release_action_pins, test_release_gate_sharding).
- Targeted Pyright: 0 errors, 0 warnings. Ruff 0.15.15 lint and format: passed for the plugin and both modified test modules.
- Production change: only the legacy FFmpeg prerequisite and actual-call condition. No dependency, coverage threshold, permissions, action pins or timeout changes.

Full local aggregate and exact-head hosted counts remain pending; focused results do not establish those outcomes.
