# Apply progress

2026-10-01: Created independent V13 preparation snapshot from sealed V12 archive. V12, existing Linux/Mac candidates and GitHub branches remain unchanged. Proposal/spec/design preceded production changes.

Metadata RED observed expected 2.2.0 versus actual 2.1.0; synchronized Python/Node metadata and own-package lock entries then passed, with `uv lock --check --offline` successful and no dependency-version changes. Current source notes explicitly distinguish the unreleased 2.2.0 beta/source candidate from the unchanged V12 Mac app.

CI RED observed 20 new failures before implementation; GREEN passed 30 focused/new-and-existing workflow checks. Final focused coverage passed 80 tests across the CI gate, unchanged workflow contracts, aggregate selection and complete-manifest sharding. The actual new wrapper ran all 360 Electron tests with 0 failed/cancelled/skipped/TODO, including the locked Qt-free preflight. Separate jobs prevent a legacy-gate failure from silently omitting Electron. The entire npm subprocess group has a bounded timeout, and errors/missing/duplicate/inconsistent summaries fail closed.

Independent review identified a missing Electron hidden-artifact upload option before the final freeze. Scoped RED observed one failure and one pass; both explicitly scoped evidence uploads now retain hidden files, and 37 related checks passed afterward. No whole-workspace artifact wildcard was added.

Dependency-inventory RED observed three missing-supplement failures; GREEN covers every 32-package headless pin and 36-entry npm lock record. Coordinator reran 21 metadata/current-document/license checks with the full legacy conftest, all passed. Runtime/engine/packaging source and all independent watcher-delta paths remain unchanged relative to V12.

Source is now frozen for the final whole-manifest aggregate and independent review. Their exact results and before/after seal belong in the matching external evidence, not retroactively in these pre-freeze notes. A failed check requires a fresh freeze and rerun; no old success is substituted. No source or binary publication has occurred.

The first complete aggregate attempt (provisional seal `7e68d7712584b9020b0aeb019df4ab7a2dd3a7aaf22c4c0e7c7cd792c36efdee`) passed 30 batches before stopping at batch 31/40 on two preparation integration contracts: the old four-action inventory versus the new eight-action workflow, and the removed durable-written-offer phrase. Failure evidence is retained. The pin test now enforces exact per-workflow multiplicities plus every reviewed SHA/version comment; cautious offer-review wording is restored without weakening its test. After correction, 84 related CI checks and 19 packaging/license checks passed. The entire aggregate must rerun from fresh collection and coverage on a new seal; no old batches are reused.
