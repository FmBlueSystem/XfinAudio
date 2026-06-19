# Design: Audio analyzer adapter boundary

Add a small analyzer boundary in `xfinaudio.audio.analyzer`: a `SpectralAnalyzer` Protocol and `LibrosaSpectralAnalyzer` adapter that delegates to the existing `analyze_spectral_profile` function.

`library.scan_service` and `desktop.spectral_completion_worker` receive optional analyzer dependencies and default to the adapter. No algorithm or file-writing behavior changes.
