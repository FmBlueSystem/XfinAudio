# Apply progress

2026-09-30: proposal/spec/design/tasks reviewed before production changes. Applying incremental local slices in declared chain. Shared test interpreter and isolated synthetic/offscreen environment; no real audio or accounts accessed.

Slice A: RED reproduced the fresh lightweight-empty → visible-full-plan path with hidden variants/Apply. GREEN now computes visibility on all renders, defaults to balanced, preserves selection and exposes requested count/readiness/pool reasons inline. REFACTOR keeps the row cache and uses one selection-detail helper. VERIFY: 42 Build/controller tests passed, lint and format passed.
