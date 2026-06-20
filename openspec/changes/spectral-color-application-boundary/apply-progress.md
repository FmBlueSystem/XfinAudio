# Apply Progress

- 2026-06-20: Scan showed direct desktop imports of `audio.spectral_profile.format_spectral_color` in rendering, library view model, and review view model.
- 2026-06-20: RED added application spectral display and desktop import-boundary tests; focused run failed because `xfinaudio.application.spectral_profile_display` did not exist and desktop imported the audio formatter directly.
- 2026-06-20: GREEN added `format_application_spectral_color()` and updated rendering, library view model, and review view model to delegate through application.
