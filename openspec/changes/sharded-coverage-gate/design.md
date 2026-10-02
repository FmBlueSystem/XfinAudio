# Design

A small pytest plugin writes structured collection JSON and optionally checks an expected batch manifest. A standalone runner launches collection and whole-file batches using its current Python interpreter, coverage parallel mode and explicit pyproject.toml configuration. It stores manifests/logs in a new evidence directory outside the checkout and checks Python/config fingerprints before and after. Environment-injected pytest selection options are rejected.

The release gate substitutes only its tests-and-coverage command when --coverage-batch-size is selected. Other gates and manual-status handling remain unchanged. Check-only output/report shows the exact selected mode.

References: [pytest collection hooks](https://docs.pytest.org/en/stable/reference/reference.html#pytest.hookspec.pytest_collection_finish), [coverage combine](https://coverage.readthedocs.io/en/latest/commands/cmd_combine.html).
