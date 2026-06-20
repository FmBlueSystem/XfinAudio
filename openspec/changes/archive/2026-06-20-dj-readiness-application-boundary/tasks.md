# Tasks

1. RED: Add application use-case tests for DJ readiness report construction and optional Serato context passthrough.
2. RED: Add desktop controller test proving readiness report construction is injected/delegated.
3. GREEN: Add `xfinaudio.application.dj_readiness` and lazy package exports.
4. GREEN: Update `DjReadinessController` to use the application boundary by default and injected builders in tests.
5. REFACTOR: Keep types/names focused and avoid UI/business coupling.
6. VERIFY: Run focused tests, then full gates.
