# Requirements

- GIVEN the 2.2.0 source candidate, WHEN Python and Electron metadata/locks are read, THEN versions agree and current documentation identifies an unreleased beta/source candidate without relabeling V12 binaries.
- GIVEN default pull-request CI, WHEN checks run, THEN the complete Python manifest is verified using the supported whole-file sharded aggregate at batch target 120 and the unchanged configured 89% floor.
- GIVEN an Electron suite run, WHEN the locked Qt-free interpreter is selected, THEN every discovered Node test executes; failures, missing results, cancellation or skipped cases cannot yield a green gate. Test counts are observed, not hardcoded.
- GIVEN failed tests, WHEN artifacts are uploaded, THEN actual stage outcome and available raw summaries remain evidence; an earlier green snapshot is never substituted.
- GIVEN source-only publication planning, WHEN dependencies are documented, THEN their pinned versions/license metadata and runtime/toolchain/legacy roles are distinguished; binary closure hashes/nonempty notice directories are not represented as legal clearance.
- GIVEN the unchanged remote baseline and independent watcher head, WHEN publication is coordinated later, THEN only a new branch/explicit draft chain may be proposed; source identity is verified and unexpected remote changes require reconciliation.
