# Design: core-lazy-exports

## Architecture impact
`xfinaudio.library.__init__` and `xfinaudio.audio.__init__` currently import service/analyzer modules eagerly. Python executes package `__init__.py` before importing submodules, so even pure imports can load heavier service/infrastructure modules.

## Approach
Use the package export pattern already established in `recommendation`, `exporting`, and `quality`:

- `_EXPORTS` maps public package names to implementation modules.
- `__getattr__` imports and caches symbols only when accessed.
- `TYPE_CHECKING` imports preserve IDE/pyright visibility without runtime coupling.
- `__all__` preserves the public export list.

## Safety
This is a package-boundary refactor only. It does not change audio analysis, DSP, export bytes, Serato behavior, recommendation scoring, or desktop UI behavior.
