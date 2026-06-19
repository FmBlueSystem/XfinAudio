# Apply progress: Audio analyzer adapter boundary

- Created approved issue #129.
- RED failed with missing `xfinaudio.audio.analyzer`.
- Added `SpectralAnalyzer` protocol and `LibrosaSpectralAnalyzer` adapter.
- Injected analyzer dependencies into scan service and spectral completion worker.
- Updated tests to patch/use the adapter boundary.
- Fresh review found two leaky paths: parallel `scan_folder` still used `analyze_paths(...)` without injection, and `MetadataScanService.scan()` did not expose/pass `spectral_analyzer`.
- Added RED coverage for parallel scan-folder analysis and the `MetadataScanService` facade path.
- Fixed `analyze_paths(...)`, scan service forwarding, and removed the obsolete spectral completion helper.
- Focused analyzer/scan/worker/batch tests passed: 24 tests.
- Pyright passed.
- Ruff check and format check passed.
- Full release gate passed: 915 tests, 90.31% coverage, pyright, ruff, format, release smoke, docs/artifact/source-package/PyInstaller checks.
