# Apply progress

2026-09-30: proposal/spec/design/tasks reviewed before production changes. Applying incremental local slices in declared chain. Shared test interpreter and isolated synthetic/offscreen environment; no real audio or accounts accessed.

Slice A: RED reproduced the fresh lightweight-empty → visible-full-plan path with hidden variants/Apply. GREEN now computes visibility on all renders, defaults to balanced, preserves selection and exposes requested count/readiness/pool reasons inline. REFACTOR keeps the row cache and uses one selection-detail helper. VERIFY: 42 Build/controller tests passed, lint and format passed.

Slice B: RED found the missing real source catalog, absent runtime resolver and missing wheel data declaration (5 failing cases). GREEN added the shared source/wheel/PyInstaller resolver and wheel data mapping, then routed icon and translations through it. Existing smoke fake now implements setWindowIcon because the real icon is reachable. VERIFY: 34 asset/packaging/catalog tests passed. Built sdist and wheel outside checkout; extracted wheel imported from /tmp and loaded the real Spanish catalog and icon successfully.
