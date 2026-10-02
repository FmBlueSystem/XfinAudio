# Verification

## Confirmed correction

- RED: new domain/cache/tag regressions yielded 13 failures and 5 passes; the independent partial display assertion also failed.
- GREEN: 478 focused tests passed in 16.61 s, including 19 actual-FFmpeg numerical cases and 18 validity cases. Changed-source Ruff, format, and targeted Pyright: clean.
- The exact 59.9/60-second boundary is covered. Short measurements retain finite integrated LUFS and true peak, omit LRA, and cannot reach the tag loader. Current complete profiles retain the approved automatic comment behavior.
- Old v1 cache/tag measurements are ineligible as current results; v2 tags are written only for complete current profiles. The tests use temporary synthetic files and repositories; numerical analysis does not invoke a tag writer, and input SHA-256 values stay unchanged.
- Nonfinite/overflow metrics, negative LRA, undefined integrated floor and invalid duration do not become complete measurements. Current typed transient failures retain their existing cache/reanalyze behavior.

## Independent numeric evidence

The production adapter was run through `/usr/bin/ffmpeg` 7.1.5 on Linux. The separate 27-case exploratory matrix used generated PCM with known amplitudes, direct ITU-R BS.1770-5 48 kHz K-weighting/block/gate equations, and pyloudnorm as a separate integrated-loudness implementation. These are not comparisons against a second invocation of the same FFmpeg meter.

- Stereo 1 kHz at -23 and -33 dBFS returned -23.0 and -33.0 LUFS; 44.1, 48 and 96 kHz checked. EBU target tolerance: ±0.1 LU.
- Mono -23 dBFS returned -26.0 LUFS under native mono weighting. Dual-mono compensation is not enabled.
- Relative and absolute gate patterns from EBU Tech 3341 cases 3–5 returned the expected -23.0 LUFS. Across finite cases, maximum difference from pyloudnorm was 0.0664 LU; direct published 48 kHz coefficient reference differed by at most 0.0330 LU.
- Two constant-level plateaus separated by 10 and 15 dB returned 10.0 and 15.0 LU LRA in the exploratory matrix. The persistent test uses two 30 s plateaus to cross the complete-profile duration boundary.
- EBU true-peak cases 15–19 returned -6.0 or +3.0 dBTP as specified, including the phase-offset intersample-overload signal whose samples remain below full scale. Accepted published tolerance: +0.2/-0.4 dBTP. Clipped sine returned +0.2 dBTP.
- Constant 3.0–3.3 s signals exposed the original 20.0 LU startup LRA artifact. They now return a partial profile without LRA; 60 s constant material returns complete LRA 0.0.
- Silence and below-gate -80 dBFS tones no longer appear as complete -70.0 LUFS measurements.

## Sources and limits

- [EBU Tech 3341](https://tech.ebu.ch/docs/tech/tech3341.pdf), §2.4 and Table 1: the meter must indicate LRA is not yet stable during the first 60 s. This is a stability-indication requirement, not an instruction to throw away LUFS/true peak, nor a guarantee of all later measurements.
- [EBU Tech 3342](https://tech.ebu.ch/docs/tech/tech3342.pdf): gated short-term loudness percentiles define LRA.
- [ITU-R BS.1770-5](https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1770-5-202311-I!!PDF-E.pdf): K-weighting, channel weighting, 400 ms blocks and gates, true peak.
- [FFmpeg ebur128](https://ffmpeg.org/ffmpeg-filters.html#ebur128): true-peak oversampling, channel and dual-mono behavior.

This is bounded numerical regression evidence, not full EBU/ITU certification or validation of the packaged macOS 7.1.1 binary. No real user audio, provider calls, listening tests, or real-library tag writes were performed. Duration still comes from scanner metadata; stale duration is not independently corrected by a new decoder-duration parser. The rounded -70 LUFS floor is rejected conservatively. Old on-disk v1 tags are ignored, not destructively removed. Full exact-integrated-commit release gate and macOS CI remain coordinator-owned.
