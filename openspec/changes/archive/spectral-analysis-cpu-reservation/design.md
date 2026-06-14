# Design: Reserve One CPU Core for UI During Spectral Analysis

## Decision question

How do we stop spectral analysis from starving the Qt UI thread without adding user-facing settings?

## Alternatives considered (Arbor-style)

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. Hard-code `cpu_count - 1` | Simple; fixes the immediate problem; no UI changes. | Not configurable on exotic hardware. | **Selected.** |
| B. Add user setting for thread count | Flexible for power users. | More UI clutter; most DJs do not want to tune this. | Rejected for now. |
| C. Use `QThread::idealThreadCount()` | Qt-native. | Still returns all cores; needs the same `-1` adjustment. | Rejected; no advantage over `os.cpu_count()`. |
| D. Lower fixed cap to 4 | Predictable. | Wastes cores on high-end machines; slow on large libraries. | Rejected. |

## Architecture impact

The default `max_workers` calculation moves from inline `min(os.cpu_count() or 4, 8)` to a shared helper:

```python
def _default_max_workers(cpu_count: int | None) -> int:
    count = cpu_count or 4
    return max(1, count - 1)
```

Applied in:
- `src/xfinaudio/audio/batch_analyzer.py` → `_default_max_workers_for_analysis()`
- `src/xfinaudio/desktop/spectral_completion_worker.py` → `_default_max_workers_for_analysis()`

Both modules keep an optional `max_workers` parameter so tests and future callers can override.

## Affected files

- `src/xfinaudio/audio/batch_analyzer.py`
- `src/xfinaudio/desktop/spectral_completion_worker.py`
- `tests/test_batch_analyzer.py`
- `tests/test_spectral_completion_worker.py`

## Safety

- No audio mutation.
- No DSP scope expansion.
- No live Serato Database V2 writes.
