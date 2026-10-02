# Proposed review chain

No PR has been published. Before publication, generate separate patchsets capped at 400 added+removed lines each; split any unit below further rather than treating this source snapshot as one review. Keep the new feature unwired until its backend/host/renderer units have passed their focused tests. Existing Qt callers retain defaults throughout.

1. Spanish error-code presentation and controller regression tests
2. Deterministic source-archive helper and dependency-symlink/escape tests
3. Existing writer's optional directory-descriptor seams plus compatibility tests
4. Native exclusive rename and new-target no-clobber tests
5. Existing-target capture/verification, retained recovery copies and overwrite-race tests
6. Conditional rollback removal and concurrent-arrival tests
7. Destination/source filesystem identity helpers and bounded IO tests
8. Exact saved/review source assessment and source-volume tests
9. Opaque read-only preview/confirmation and destination/readiness tests
10. Confirmed commit/receipt resolution, idempotency and stale-state tests
11. Main/preload/schema authority, native confirmation and shutdown-drain tests
12. Serato renderer state controller and race/cancel/navigation tests
13. Accessible export view and its rendering tests
14. Application routes, review/saved sources and dirty-editor integration tests
15. Real subprocess integration, native fixture checklist and verification documentation

Any patchset's test additions count toward its 400-line cap. Larger existing files may appear in several consecutive patchsets. Preserve strict RED→GREEN evidence for each behavioral unit; do not weaken coverage or hide failing tests to make an intermediate patch appear green.
