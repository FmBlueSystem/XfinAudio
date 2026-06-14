# Verify Report: Export Naming Polish

## Verification commands

All commands were run in order and passed.

```bash
uv run pytest tests/test_export_naming.py tests/test_export_coordinator.py -v
uv run pytest -q
uv run pyright src tests
uv run pytest --cov --cov-fail-under=70 -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/release_gate_check.py --run
```

## Results

| Gate | Status | Evidence |
|------|--------|----------|
| pytest focused | passed | 14 passed |
| pytest full | passed | 712 passed |
| pyright | passed | 0 errors, 0 warnings, 0 informations |
| pytest-cov | passed | 87.77% coverage (threshold 70%) |
| ruff check | passed | All checks passed! |
| ruff format | passed | 162 files already formatted |
| release_gate_check.py --run | passed | All automated gates passed |

## Requirement-by-requirement evidence

1. **Timestamp included**: `default_export_filename` includes `%Y%m%d_%H%M%S` from the generated timestamp.
2. **Strategy included**: The sanitized recommendation strategy name is part of the filename.
3. **Suffix included**: The DJ software identifier (e.g. `rekordbox`, `traktor`, `virtualdj`) is included when provided.
4. **Track count included**: Filename ends with `{count}_track(s)`.
5. **Filesystem-safe**: Spaces, slashes, and special characters are replaced with underscores and collapsed.
6. **Coordinator integration**: `ExportCoordinator.preview_non_serato_export` and `export_recommendation_to_non_serato` use the new utility for their default filenames.
7. **Tests**: `tests/test_export_naming.py` covers timestamp, strategy, suffix, track count, and sanitization.

## Limitations

- Only non-Serato exports use the new naming; Serato already had polished crate names.
- Callers that provide an explicit `crate_name` or use a Prep Copilot variant continue to use those names.
