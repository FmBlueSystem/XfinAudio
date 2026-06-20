# Proposal: Audio analysis planning boundary

## Intent

Extract pure spectral batch analysis planning from executor code so cache decisions and duplicate path handling can be tested without threads, processes, librosa, filesystem mutation, or UI code.

## Scope

In scope:
- Add a pure audio analysis planning module for cache-hit lookup and pending-path selection.
- Keep concrete thread/process execution in `xfinaudio.audio.batch_analyzer`.
- Avoid analyzing duplicate pending paths more than once while preserving one result key per path string.
- Add focused unit tests for the pure planning behavior and batch analyzer use.

Out of scope:
- New DSP features or changes to spectral profile extraction math.
- Audio file mutation.
- Live Serato DB V2 writes.
- UI behavior changes.
