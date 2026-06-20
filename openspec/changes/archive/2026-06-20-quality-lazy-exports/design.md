# Design: quality-lazy-exports

## Architecture impact
`xfinaudio.quality.__init__` is a package barrel. Today it eagerly imports `dj_readiness`, which pulls Serato/exporting dependencies even for pure quality-report consumers.

## Approach
Use the same lazy package export pattern adopted for `xfinaudio.exporting` and `xfinaudio.recommendation`:

- `_EXPORTS` maps public names to concrete modules.
- `__getattr__` resolves and caches exports on first access.
- `TYPE_CHECKING` imports keep pyright and IDE symbol discovery clean without runtime import cycles.

## Safety
No behavior logic changes, no dependencies, no UI, no audio mutation, no DSP, no live Serato DB V2 writes.
