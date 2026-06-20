# Design: Audio analysis planning boundary

## Approach

Create `xfinaudio.audio.analysis_planning` for pure-ish batch planning helpers that own cache lookup, cache storage, and duplicate pending-path selection. `batch_analyzer` remains the infrastructure/execution layer that chooses sequential, thread, or process execution and calls the analyzer boundary.

## Safety

The slice does not change spectral extraction math, export behavior, audio files, or Serato data. It only narrows scheduling decisions before existing analyzer execution.
