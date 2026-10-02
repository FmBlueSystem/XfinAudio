# Explicit sharded aggregate verified — 2026-10-01

Strict RED→GREEN evidence covers batch partitioning, input bounds, complete collection/execution manifests, collection drift, suppressed execution, missing/corrupt coverage data, source changes, stale coverage isolation, coverage-floor failure, aggregate command substitution and failure propagation. Forty-five focused checks passed, including existing aggregate-runner regressions.

The actual repository command completed successfully:

```sh
uv run python scripts/release_gate_check.py --run --coverage-batch-size 180 --coverage-evidence-dir OUTSIDE_NEW_DIR --report-json OUTSIDE_REPORT.json
```

The coverage phase collected and executed all 3,590 tests exactly once in 23 whole-file batches. The remaining aggregate gates retain their separate documentation/hygiene checks. The largest file can exceed the target batch size; no file was split or test omitted. Every batch's collection, execution report and coverage data were validated before combination. Combined coverage: 94.35%, with the existing pyproject.toml floor and no override. All ten aggregate gates passed; default non-sharded command behavior remains unchanged.

The test mode is now a supported aggregate option, not an external workaround or waiver. Evidence directories must be new/outside the checkout. The configured full suite and all other automated/manual gates are preserved. Optional binary packaging was not run; PyInstaller was check-only. This does not publish a release or establish new native/manual acceptance.
