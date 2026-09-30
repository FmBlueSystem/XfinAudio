# Tasks

1. RED: integrated dirty-state/banner, watcher startup/resume failure regressions.
2. GREEN/REFACTOR: publish state; recover watcher startup; real-directory fixture.
3. VERIFY: focused scan/watch/MainWindow tests and lint/types.
4. RED: subprocess close during slow scan/recommendation/AI and replacement.
5. GREEN/REFACTOR: asynchronous close, cancellation and retained worker ownership.
6. VERIFY: workflow lifecycle subprocess tests and existing service regressions.
7. RED: background shutdown keeps running work owned without terminate/block.
8. GREEN/REFACTOR: safe cooperative analysis drain and no new downstream stages.
9. VERIFY: focused analysis tests, lint/types; parent full release gate.

Integrated verification completed on 2026-09-30 at `9e7c894`: all automated release gates passed, 2921 tests and 93.54% coverage. Native validation remains separate.
