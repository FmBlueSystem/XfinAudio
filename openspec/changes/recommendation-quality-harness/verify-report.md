# Verify Report: Recommendation Quality Harness and Pool-Collapse Fix

Status: pending — verification runs after the apply phase.

## Requirement coverage (to be completed)

| Req | Description | Evidence | Status |
|-----|-------------|----------|--------|
| R1 | Read-only library loading | — | pending |
| R2 | Deterministic anchor sampling | — | pending |
| R3 | Fill-rate metric | — | pending |
| R4 | Hard-rule transition validity | — | pending |
| R5 | Energy-curve monotonicity | — | pending |
| R6 | Baseline report artifact | — | pending |
| R7 | Pool-collapse fix (PR2) | — | pending |

## Verification commands (to be run)

- [ ] `uv run pytest -q`
- [ ] `uv run pyright src tests`
- [ ] `uv run pytest --cov --cov-fail-under=70 -q`
- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run python scripts/release_gate_check.py --run`

## Baseline vs post-fix (real library, seed 1234, 40 anchors, requested 12)

| Strategy | Fill baseline | Fill post-fix | Collapse baseline | Collapse post-fix | Validity baseline | Validity post-fix |
|----------|---------------|---------------|-------------------|-------------------|-------------------|-------------------|
| warmup | 0.527 | 1.000 | 16 | 0 | 0.835 | 0.641 |
| peak_time | 0.752 | 0.990 | 7 | 0 | 0.773 | 0.671 |
| chill | 0.171 | 0.671 | 35 | 2 | 0.963† | 0.476 |

† chill's 0.963 baseline validity was an artifact of 1–2 track playlists (almost no transitions to
evaluate). After making chill optimizer-backed (harmonic sequencing instead of raw BPM sort), its
validity reflects real harmonic flow: 0.476, with fill 0.671 and collapse cut from 35 to 2.
Progression: pool-fix alone gave fill 0.552 / validity 0.269 (incoherent fill); optimizer-backing
recovered coherence to 0.476.
| build | 1.000 | 1.000 | 0 | 0 | 0.732 | 0.732 |
| harmonic_journey | 1.000 | 1.000 | 0 | 0 | 0.904 | 0.904 |
| same_color | 1.000 | 1.000 | 0 | 0 | 0.898 | 0.898 |
| same_energy | 0.979 | 0.979 | 1 | 1 | 0.897 | 0.897 |
| same_genre | 0.877 | 0.877 | 0 | 0 | 0.869 | 0.869 |
| same_vibe | 1.000 | 1.000 | 0 | 0 | 0.870 | 0.870 |

### Honest interpretation

- **warmup and peak_time: clean wins.** Collapse eliminated; fill near-maximal; validity drop is
  moderate and acceptable (~0.64–0.67), consistent with these being single-dimension-sort
  strategies.
- **chill: partial win with a real cost.** Fill 0.171→0.552 and collapse 35→11, but validity
  collapsed 0.963→0.269. Root cause: chill sorts ONLY by ascending BPM and ignores harmonic
  (Camelot) compatibility, so a *filled* chill set has many key-incompatible adjacent transitions.
  The old tiny 1–2 track sets were "valid" only because they had almost no transitions.
- **Non-filtered strategies unchanged**, confirming the fix is scoped to range-filtered strategies.

### Conclusion

The pool-collapse fix is a net improvement for warmup/peak_time and improves chill fill, but it
exposes that the filtered strategies' single-dimension sort produces harmonically incoherent sets
when filled. Strategies routed through the optimizer (harmonic_journey, same_*) keep both high fill
AND high validity. Making chill/warmup/peak_time optimizer-backed (while honoring their
energy/BPM intent) is the follow-up that would recover validity — tracked as a separate change.

## Verification commands (executed)

- [x] `uv run pytest -q` — 882 passed
- [x] `uv run pyright src tests` — 0 errors, 0 warnings
- [x] `uv run pytest --cov --cov-fail-under=70 -q` — 89.68% (≥70%)
- [x] `uv run ruff check .` — All checks passed
- [x] `uv run ruff format --check .` — 197 files formatted
- [x] `uv run python scripts/release_gate_check.py --run` — PASS

## Requirement coverage

| Req | Description | Evidence | Status |
|-----|-------------|----------|--------|
| R1 | Read-only library loading | TrackRepository.list_tracks; no writes | met |
| R2 | Deterministic anchor sampling | test_sample_anchors_is_deterministic_for_seed | met |
| R3 | Fill-rate metric | test_fill_rate_*; baseline table | met |
| R4 | Hard-rule transition validity | test_transition_* | met |
| R5 | Energy-curve monotonicity | test_energy_monotonic_*; warmup 0.957 | met |
| R6 | Baseline report artifact | baseline-report.md | met |
| R7 | Collapse fix | warmup/peak_time collapse→0; chill 35→2 | met (validity tradeoff documented) |
