# Spectral Color Application Boundary Specification

## Requirement: Application formats spectral color display text
- GIVEN a spectral profile or no profile WHEN application display formatting is requested THEN it returns the same compact badge text as the existing audio formatter.

## Requirement: Desktop remains adapter
- GIVEN desktop rendering and view models WHEN spectral color display text is needed THEN desktop calls the application boundary, not `xfinaudio.audio.spectral_profile.format_spectral_color` directly.
