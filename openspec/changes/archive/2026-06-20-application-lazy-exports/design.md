# Design: application-lazy-exports

## Architecture impact
`xfinaudio.application.__init__` eagerly imports workflow and vertical-flow modules. Python executes package `__init__.py` before submodule imports, so isolated application imports can load sibling orchestration modules unnecessarily.

## Approach
Use the established lazy package export pattern:

- `_EXPORTS` maps public symbols to implementation modules.
- `__getattr__` resolves and caches public exports on first access.
- `TYPE_CHECKING` imports keep pyright/IDE visibility without runtime coupling.
- `__all__` remains stable for public API compatibility.

## Safety
Package-boundary refactor only. No workflow behavior, UI, audio, DSP, Serato DB V2, or export format changes.
