# Proposal: Reserve One CPU Core for UI During Spectral Analysis

## Intent

Prevent the desktop UI from becoming sluggish while spectral profile analysis runs by reserving at least one CPU core for Qt and the operating system.

## Scope

### In scope

- Cap spectral analysis worker pools at `max(1, cpu_count - 1)` threads.
- Apply the cap to both the scan-time batch analyzer and the background spectral completion worker.
- Keep the change deterministic and testable without requiring real audio.

### Out of scope

- User-configurable thread count (can be added later if needed).
- Changing analysis algorithm, caching, or cancellation behavior.
- Other background workers (recommendation, scan metadata) are unchanged.

## Motivation

QA showed that while `SpectralCompletionWorker` runs, the app becomes unresponsive because the worker pool uses all available cores. DJs cannot interact with the UI until analysis finishes.

## Success criteria

1. On an N-core machine, spectral analysis uses at most `N-1` workers (minimum 1).
2. Existing tests for batch analysis and spectral completion still pass.
3. All verification commands pass.
4. No audio files are mutated.

## Rollback plan

- Revert the two `max_workers` calculations to `min(os.cpu_count() or 4, 8)`.

## Review budget

Estimated changed lines: ~20 production + ~40 test lines, well within the 400-line budget.
