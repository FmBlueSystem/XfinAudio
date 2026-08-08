# Specification: Spectral Cohesion Control

## Glossary

- **Spectral profile**: per-track `SpectralProfile` with RGB ratios and a dominant color (`RED`, `GREEN`, `BLUE`, `MIXED`).
- **Spectral cohesion**: a value in `[0.0, 1.0]` controlling how strongly recommendations prefer similar spectral colors.

## Requirements

### R1. Cohesion parameter in scoring

**GIVEN** two adjacent tracks with spectral profiles  
**WHEN** `spectral_cohesion` is `0.0`  
**THEN** the spectral component uses its base weight and no color-difference penalty is applied.

**GIVEN** two adjacent tracks with different dominant colors  
**WHEN** `spectral_cohesion` is `1.0`  
**THEN** the transition total score is lower than with `spectral_cohesion` `0.0`.

**GIVEN** two adjacent tracks with the same dominant color  
**WHEN** `spectral_cohesion` is any value in `[0.0, 1.0]`  
**THEN** no color-difference penalty is applied.

**GIVEN** two adjacent tracks where at least one lacks a spectral profile  
**WHEN** scoring is computed  
**THEN** no color-difference penalty is applied and the spectral component is omitted from the weighted total.

### R2. Valid range

**GIVEN** a `TransitionScoringConfig`  
**WHEN** `spectral_cohesion` is set outside `[0.0, 1.0]`  
**THEN** construction raises `ValueError`.

### R3. Same Color strategy

**GIVEN** the strategy registry  
**WHEN** "Same Color" is selected  
**THEN** it uses a weight profile that emphasizes spectral similarity while retaining harmonic, BPM, energy, and tag components.

### R4. Build Playlist UI

**GIVEN** the Build Playlist screen  
**THEN** a "Spectral Cohesion" slider is visible with range 0%–100% and a percentage label.

**GIVEN** the slider  
**WHEN** the user moves it  
**THEN** the new value is persisted to `AppSettings` immediately.

**GIVEN** a persisted cohesion value  
**WHEN** the app restarts  
**THEN** the slider is restored to that value.

### R5. End-to-end wiring

**GIVEN** the user clicks "Recommend Playlist"  
**WHEN** the slider is at X%  
**THEN** the recommendation uses `spectral_cohesion = X / 100`.

## Non-functional

- The change must not break existing transition scoring tests when `spectral_cohesion=0.0`.
- The change must stay within the 400-line review budget.
