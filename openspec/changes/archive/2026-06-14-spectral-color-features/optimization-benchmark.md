# Spectral Analysis Optimization Benchmark

**Folder:** `/var/folders/k2/vcwk4xx51gl9y8mxrd9mqjvh0000gn/T/xfinaudio_spectral_bench_5i4_arkl/bench_20_60.0s`
**Tracks:** 20
**Duration per track:** 60.0s
**Timestamp:** 2026-06-14T15:59:54Z

| Config | Median seconds | Throughput (tracks/sec) | Notes |
|---|---|---|---|
| sequential | 1.110 | 18.02 |  |
| parallel | 0.414 | 48.31 | 2.68× vs sequential |
| thread | 0.485 | 41.23 | 2.29× vs sequential |
| cached | 0.489 | 40.88 | 2.27× vs sequential |
| cached-rescan | 0.000 | 383233.55 | 21272.48× vs sequential |

## Accuracy check
- **parallel**: 0 dominant-color mismatches vs sequential
- **thread**: 0 dominant-color mismatches vs sequential
- **cached**: 0 dominant-color mismatches vs sequential
- **cached-rescan**: 0 dominant-color mismatches vs sequential
