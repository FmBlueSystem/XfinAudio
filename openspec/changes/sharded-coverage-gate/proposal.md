# Explicit fresh-process coverage gate

Add an opt-in `--coverage-batch-size N` to the existing aggregate release gate. Preserve the default command and every other gate. The new mode runs the same collected tests in fresh processes, combines isolated coverage data, and applies the existing pyproject.toml floor once to the complete run. This is resource isolation, never a waiver, subset selector or replacement for manual/native acceptance.

Chained review units capped at400 added+removed lines: collection-evidence plugin and tests; batching/coverage runner and tests; aggregate CLI wiring and tests; documentation/integration evidence. No publish or release.
