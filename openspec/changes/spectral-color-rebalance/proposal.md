# Proposal: Rebalance Spectral Color Classification

## Intent
The spectral "color" feature is bass-biased: across the real 10,607-track library the stored
profiles are 81% RED, 0% BLUE (8643 RED / 1450 MIXED / 509 GREEN / 0 BLUE). Linear mel-energy
ratios let low-frequency energy (which dominates music) win almost every time, so the Color column
gives no useful signal.

## Evidence (measured on a 50-track real sample)
- Current (linear energy): RED 43, MIXED 5, GREEN 2 (86% RED) — matches the global bias.
- Frequency-weighted (energy x center frequency) + 0.45 threshold: GREEN 31, MIXED 13, BLUE 4,
  RED 2 — all four colors discriminate. Synthetic pure tones still classify to their band
  (subbass/red->RED, green->GREEN, blue/veryhigh->BLUE).

## Scope (in)
- `analyze_spectral_profile`: weight each mel band's energy by its center frequency before
  computing red/green/blue ratios, counteracting music's natural low-frequency energy
  concentration.
- `_dominant_color`: lower the dominance threshold 0.55 -> 0.45 so a clear plurality wins.

## Out of scope
- Re-scanning the existing library (the stored RED profiles persist until a re-scan; the code
  change governs all future scans/spectral completion).
- Changing band boundaries or the SpectralProfile schema.

## Success criteria
1. Synthetic tone assets classify to their expected band (regression).
2. On a real sample, no single color exceeds ~60% and all of RED/GREEN/BLUE appear.
3. All verification commands pass.

## Rollback
Revert the weighting line and restore the 0.55 threshold.
