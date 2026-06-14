# Specification: Reserve One CPU Core for UI During Spectral Analysis

## Requirements

### R1. Background spectral completion worker

**GIVEN** a machine with `N` CPU cores  
**WHEN** `SpectralCompletionWorker` starts  
**THEN** it uses at most `max(1, N - 1)` worker threads.

**GIVEN** a single-core machine  
**WHEN** `SpectralCompletionWorker` starts  
**THEN** it uses exactly 1 worker thread.

### R2. Scan-time batch analyzer

**GIVEN** a machine with `N` CPU cores  
**WHEN** `analyze_paths` is called with the default `max_workers`  
**THEN** it uses at most `max(1, N - 1)` worker threads.

**GIVEN** `analyze_paths` is called with an explicit `max_workers` value  
**THEN** that explicit value is respected.

### R3. Deterministic test seam

**GIVEN** a caller provides a fake `cpu_count`  
**WHEN** the worker or analyzer computes its default pool size  
**THEN** the result is `max(1, fake_cpu_count - 1)`.

## Non-functional

- The change must not break existing spectral analysis tests.
- The change must stay within the 400-line review budget.
