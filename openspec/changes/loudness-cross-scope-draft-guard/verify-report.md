# Verification
- All six scopes: visible exact labels, disabled loudness actions, explicit resolve navigation, preserved field values, enabled Save/Discard; direct guarded preview/run still reject
- Combined drafts, explicit save/discard, clean startup/reload, no-op and revert: PASS
- Repeated preview, native cancellation, late navigation/focus safety: PASS
- Same-page AI draft/discard synchronizes Delete and guidance: PASS
- Import recovery links remain usable while import stays blocked: PASS
- TypeScript and final supported scripts/electron_ci_check.py: 379 passed, 0 failed/skipped/cancelled/todo; Qt-free preflight and npm exit 0
- Evidence: external reanalyze-ui-evidence/after-import/electron-test-report.json and electron-test.log; earlier RED evidence retained
- Legacy Python release gate attempted but blocked before tests: tests/conftest.py imports absent PySide6 in intentionally Qt-free V9 interpreter. No environment change made
- Real native viewport/keyboard and combined release verification pending; Node mock DOM focus does not prove native layout
