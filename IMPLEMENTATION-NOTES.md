# Implementation Notes

## add-loudness-module WU1a

- The minimum loudness duration is **3.0 seconds**. EBU R128 short-term loudness uses a
  3-second window, so this is the smallest duration at which LRA and true-peak values are
  retained by this module. Shorter material still preserves integrated LUFS and is typed
  `too_short` with LRA and dBTP unset.
- The golden fixture was captured from FFmpeg 8.0.1 against the synthetic 1 kHz WAV; the shipped bundle must use the same parser fixture or replace it when its pinned build is selected.
- `pyloudnorm` is a development-only conformance oracle. The runtime adapter remains the
  pinned FFmpeg command/parser boundary and never imports or invokes `pyloudnorm`.
- Process execution, preflight, timeout, cancellation, and orphan reaping remain WU1b.
