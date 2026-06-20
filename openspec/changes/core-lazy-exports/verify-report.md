# Verify report: core-lazy-exports

## Requirement: Library pure model imports stay isolated

### Evidence
- RED confirmed importing `xfinaudio.library.models` loaded `xfinaudio.library.scan_service` and `xfinaudio.library.track_repository` through eager package exports.
- GREEN focused test now passes in a fresh Python process: `xfinaudio.library.models` does not load scan services or repositories.

## Requirement: Audio planning imports stay isolated

### Evidence
- RED confirmed importing `xfinaudio.audio.analysis_planning` loaded analyzer/spectral modules.
- GREEN focused test now passes in a fresh Python process: `xfinaudio.audio.analysis_planning` does not load `xfinaudio.audio.batch_analyzer` or `xfinaudio.audio.spectral_profile`.
- `SpectralProfile` references in `analysis_planning` are now type-only/runtime-safe.

## Requirement: Public package exports remain compatible

### Evidence
- Focused subprocess test confirms `from xfinaudio.audio import AnalysisPlan, analyze_paths` and `from xfinaudio.library import TrackRecord, scan_folder` resolve successfully.

## Full verification
- `uv run pytest -q` -> 956 passed.
- `uv run pyright src tests` -> 0 errors, 0 warnings.
- `uv run pytest --cov --cov-fail-under=70 -q` -> 956 passed, total coverage 89.77%.
- `uv run ruff check .` -> pass.
- `uv run ruff format --check .` -> 230 files already formatted.
- `uv run python scripts/release_gate_check.py --run` -> pass, including release readiness smoke, publication docs, artifact hygiene, source package hygiene, PyInstaller check-only, and root artifact hygiene.
