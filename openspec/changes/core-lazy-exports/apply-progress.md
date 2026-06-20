# Apply progress: core-lazy-exports

## Status
Applied.

## RED
- `uv run pytest tests/test_core_package_import_boundaries.py -q`
- Failed as expected:
  - `xfinaudio.library.models` loaded `xfinaudio.library.scan_service` / `xfinaudio.library.track_repository` through eager package exports.
  - `xfinaudio.audio.analysis_planning` loaded `xfinaudio.audio.batch_analyzer` / `xfinaudio.audio.spectral_profile` through eager/type-only imports.

## GREEN
- Converted `xfinaudio.library.__init__` to lazy public exports.
- Converted `xfinaudio.audio.__init__` to lazy public exports.
- Made `xfinaudio.audio.analysis_planning` use type-only `SpectralProfile` references so planning imports do not load spectral analysis.

## Focused evidence
- `uv run pytest tests/test_core_package_import_boundaries.py tests/test_scan_service_analyzer_boundary.py tests/test_audio_analysis_planning.py -q` -> 8 passed.
- `uv run pyright src/xfinaudio/library/__init__.py src/xfinaudio/audio/__init__.py src/xfinaudio/audio/analysis_planning.py tests/test_core_package_import_boundaries.py` -> 0 errors, 0 warnings.
- `uv run ruff check ...` and `uv run ruff format --check ...` -> pass.
