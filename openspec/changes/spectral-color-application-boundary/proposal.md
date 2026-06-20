# Spectral Color Application Boundary

Move spectral color display formatting behind an application-layer boundary so desktop presentation code does not import audio-domain formatting helpers directly.

In scope: application spectral color display formatter, desktop delegation in rendering/library/review view models, focused tests, SDD evidence.
Out of scope: changing spectral profile calculation, DSP/audio analysis, audio mutation, export formats, live Serato DB V2 writes.

Success: desktop no longer imports `format_spectral_color` from `xfinaudio.audio.spectral_profile`; UI text remains unchanged.
