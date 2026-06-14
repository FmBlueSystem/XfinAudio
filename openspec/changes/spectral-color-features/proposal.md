# Proposal: Spectral Color Features

## Intent

Add lightweight, read-only spectral analysis to XfinAudio so the recommender can detect when two technically compatible tracks (same BPM, compatible key, similar energy) still clash because of different spectral texture (e.g., one track is bass-heavy/red and the other is mid/bright/green or blue).

This proposal also formally changes the project rule that prohibited waveform analysis/DSP, limiting that prohibition to destructive or real-time audio processing while allowing offline, read-only spectral feature extraction.

## Motivation

Manual QA showed that BPM, key, and energy are not enough to guarantee a good transition. A track can look perfect on paper but sound wrong because the frequency balance changes abruptly. Existing metadata (Mixed In Key energy, Serato autogain, tags) does not capture this texture reliably, and manually tagging 10,000+ tracks is not practical.

## Scope

### In scope

- Extract read-only spectral features from audio files during scan:
  - Mel-frequency energy ratios (red/grave, green/mid, blue/high bands).
  - Spectral centroid and rolloff for brightness checks.
  - RMS/dynamics for loudness texture.
- Cache features in the app-owned SQLite database keyed by absolute file path.
- Add a deterministic spectral similarity score to transition scoring.
- Expose a per-track color profile (e.g., RED/GREEN/BLUE/MIXED) in the library and review UI.
- Add a review warning when adjacent tracks have a large spectral jump.
- Keep the feature optional/fallback-friendly: tracks that cannot be analyzed are still usable with existing metadata scores.

### Out of scope

- BPM detection, key detection, beatgrid detection, downbeat/phrase detection.
- Audio mutation, rendering, mixing, crossfades, EQ, time-stretching, pitch-shifting.
- Real-time analysis during playback.
- Replacing Mixed In Key or Serato analysis.
- Writing anything to audio files or Serato Database V2.

## Rule change

The `gentle-ai-sdd-tdd` skill currently states:

> Do not add DSP, audio rendering, mixing, time-stretching, pitch-shifting, or waveform analysis.

This change updates that rule to:

> Do not add audio rendering, mixing, time-stretching, pitch-shifting, destructive audio mutation, or real-time waveform analysis. Read-only, offline spectral feature extraction is allowed when cached, optional, and not used to derive BPM/key/beatgrid.

## Architecture decision

The analyzer will be implemented in **Python using librosa + numpy**, not in C/C++ or Rust.

Rationale:
- C/C++ is explicitly prohibited by the current `gentle-ai-sdd-tdd` skill.
- Rust (e.g., PyO3) would add a new toolchain and native build complexity disproportionate to the gain.
- Benchmarks show Python + librosa is fast enough with the right optimizations:
  - ~2.1s per track sequential (load + mel-spectrogram on FLAC).
  - ~0.12s per track if audio is already loaded.
  - Estimated ~43 minutes for 10k tracks using 8-core multiprocessing.
- Optimizations: `sr=22050`, `n_mels=64`, `n_fft=1024`, `ProcessPoolExecutor`, incremental re-scan, and UI cancellation.

A Rust rewrite will be reconsidered only if real-world profiling shows Python remains too slow after all optimizations.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Heavy dependency (librosa/numpy/scipy) | High | Pin upper bounds in `pyproject.toml`; keep analysis optional so the app still works if the dependency is missing. |
| Slower scan for 10k tracks | Medium | Use `ProcessPoolExecutor` for multiprocessing; run in the existing worker thread with cancellation; cache results; incremental scan only re-analyzes changed files. |
| Legal posture shift | Medium | Document that this is read-only analysis, not redistribution of derived audio; update `NOTICE.md` if needed. |
| Accuracy on compressed or mono files | Medium | Validate against synthetic fixtures and manual labels; fallback to metadata-only scoring on failure. |
| Scope creep into full DSP | High | Strictly limit to energy ratios, centroid, rolloff, RMS; reject BPM/key/beat detection. |

## Rollback plan

1. Remove the spectral analysis module and its dependency.
2. Drop the new columns from the SQLite schema (or leave them nullable and unused).
3. Remove the spectral score from transition scoring.
4. Restore the original DSP prohibition in the skill/config.

## Success criteria

- [ ] Synthetic color fixtures (`assets/synthetic_color_tests/`) classify as RED/GREEN/BLUE under the new analyzer.
- [ ] Manually labeled tracks (Funkytown=red, Ring My Bell=green, etc.) classify consistently with the analyzer.
- [ ] Spectral features are cached in SQLite and survive app restart.
- [ ] Transition scoring includes a spectral similarity component.
- [ ] Review UI shows a warning when adjacent tracks have a large spectral jump.
- [ ] Scan remains cancellable and incremental.
- [ ] All verification commands pass.
- [ ] No audio files are mutated.
