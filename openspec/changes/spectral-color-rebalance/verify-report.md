# Verify Report: Rebalance Spectral Color Classification

## Change
- analyze_spectral_profile weights band energy by sqrt(center frequency) before computing ratios.
- _dominant_color threshold lowered 0.55 -> 0.45.

## Evidence (real audio, 100-track sample, full-track analysis)
| Weighting | Distribution | Top color |
|-----------|--------------|-----------|
| linear (current) | RED 84, GREEN 16 | 84% |
| f^0.3 | RED 61, GREEN 39 | 61% |
| **f^0.5 (chosen)** | **RED 43, GREEN 51, MIXED 6** | **51%** |
| f^1.0 | GREEN-biased, over-corrected | — |

Synthetic tones still classify to their band: subbass/red->RED, green->GREEN, blue/veryhigh->BLUE.

## Result
Top color dropped from 84% to 51%; RED/GREEN/MIXED all present with balance; BLUE rare but
reachable (genuinely bright tracks / synthetic blue tones). Meaningful discrimination restored.

## Note
Existing stored profiles remain at their old values until a re-scan; the change governs all future
scans and background spectral completion.

## Verification commands
- [x] uv run pytest -q — 913 passed
- [x] uv run pyright src tests — 0 errors
- [x] uv run ruff check / format — clean
