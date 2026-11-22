# XfinAudio 2.39.0 Release Notes

Date: 2026-11-22

## Summary

2.39.0 is an **unreleased beta/source candidate** built on 2.38.0. It attacks
the analyzer that dominates profile completion: danceability was ~93% of the
per-track profile time, and HPSS median filtering was 97% of danceability. This
release computes the same HPSS in a cheaper way, so **a track's danceability
analysis is 3.6x faster** and **a library-wide profile pass is 2.9x faster** at
the same two workers — with **every stored value unchanged**.

## What got faster

Measured per-stage on 12 FLAC tracks (one per genre, read-only, three rounds
interleaved against a frozen copy of the previous code, because a profile run
was sharing the CPU):

| Stage (per-track median) | Before |
|---|---|
| duration probe | 96 ms |
| `librosa.load` | 200 ms |
| onset strength | 24 ms |
| pulse clarity | — |
| tempogram | 14 ms |
| STFT | 11 ms |
| **HPSS** | **1561 ms** |
| energy sums | 9 ms |
| **total** | **1979 ms** |

The two `scipy.ndimage.median_filter` calls inside HPSS were 1518 ms of that
1561 ms. The result:

- **Per track: 1979 ms -> 549 ms (3.61x).**
- **Profile pass at the existing 2 workers: 59.8 -> 173 tracks/min (2.9x).**

How: `|H| + |P|` needs only the magnitude, so HPSS is now computed from `|S|`
with librosa's own soft masks (same power and `split_zeros` semantics) instead
of masking a complex STFT, and the two 31-frame medians are selected in
bit-identical row blocks on a bounded pool of `min(4, cores // 2)` threads.

## Nothing stored changes

- Drift against the previous code on those 12 tracks: **score 7.99e-8**,
  percussive_ratio 2.26e-8, pulse_clarity 0, tempo_confidence 0 — far inside the
  1e-6 tolerance this work holds itself to.
- **`CURRENT_DANCEABILITY_VERSION` stays 1.** No profile is rewritten,
  re-measured or invalidated: **existing profiles stay valid** and a library
  whose danceability analysis is already complete stays complete.
- The analysis remains **read-only**: no source audio is modified, and it still
  writes no live Serato database V2 file.

## Measured and not shipped

Every option below was measured and left out, because it either bought too
little or changed values:

- single soft mask instead of two: 5% faster, changes values.
- reusing the mel STFT for the harmonic/percussive split: 2.7%.
- BLAS environment settings: no BLAS call in the hot path, so no gain.
- numba median: slower than the blocked selection.
- shrinking the STFT: faster, changes values.
- **process-level parallelism in the profile pass: not shipped.** The pass is
  **not GIL-bound** — the previous analyzer already ran 2.36x faster on 2
  threads at cpu/wall 1.72 — so moving the pass to processes would add
  cancellation, per-track failure counting and writer complexity for no measured
  gain. It stays a documented option if a future analyzer becomes GIL-bound.

## How it was verified

- `python scripts/bench_danceability.py` — the same 12 tracks, three rounds,
  before/after interleaved in the same machine conditions: 1979 -> 549 ms per
  track, 59.8 -> 173 tracks/min per pass, per-value drift reported above.
- `pytest tests/audio/test_danceability_hpss_equivalence.py tests/audio/test_danceability.py`
  — 38 passed. The equivalence test pins the new magnitude path against
  `scipy.ndimage.median_filter` and `librosa.decompose.hpss` on the same input.
- `pytest tests/test_electron_candidate_metadata.py` and the release-docs tests —
  pyproject, `uv.lock`, `desktop-electron/package.json`,
  `desktop-electron/package-lock.json` and this file agree on 2.39.0.

## Known limitations

- The 12-track measurement is a **genre mix of FLAC only**: `por_genero` holds
  no MP3 (10 390 files, all FLAC), so the format mix originally planned for the
  measurement could not be taken.
- The 3.6x and 2.9x numbers belong to the measurement machine while another
  profile run shared the CPU. Compare like for like before quoting them
  elsewhere.
- Blocked medians use a bounded thread pool inside one analysis, so a single
  very long track now briefly uses more than one core.
- The 2.39.0 candidate is source-only: no installer, updater or binary
  redistribution is claimed by this version.
