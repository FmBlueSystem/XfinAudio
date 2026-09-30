# Verification
2026-09-30 focused verification on the UI chain:
- `PYTHONPATH=src python -m pytest -q tests/test_optional_ai*.py`: 18 passed.
- Ruff check and format over new modules/tests: passed.
- Pyright with the shared virtualenv explicitly selected: 0 errors.
- Requirements covered: default-off consent plus global enablement; GUI-thread capture and background service work; cancellation, retry and retained old workers; changed request/context and recipient; editable Library filters awaiting Apply; engine-validated Editor preview with explicit canonical command and no automatic draft/save; saved-set opaque-ID selection, local evidence and repository recheck; bounded plain-text Metadata/Live commentary and stale Next rejection; prerequisites and existing offline controls retained.
- Tests use synthetic records, temporary HOME/repositories and injected services only. No network, real credentials, audio operations or dependencies were used.
- Parent owns MainWindow installation/close/invalidation hooks, merged responsive screenshots and exact-commit aggregate release gate. Those combined checks remain pending here; focused success is not a release-gate claim.
