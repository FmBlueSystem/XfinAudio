2026-10-01: isolated v6 checkout from verified v5. V5 remains frozen for native validation. Specification/design/tasks complete; strict test-first work begins.

## 2026-10-01 implementation checkpoint

- Settings/read-only rescan: 45 focused headless checks pass; added finite/bounded giant-integer rejection after a demonstrated OverflowError RED.
- Observer: actual Linux Worker tests cover nested changes, ignored app data, unavailable/linked trees, new/replaced directories and actual exit. Replaced-directory test initially failed because the old inode's watch survived; handles now carry identity and are replaced.
- Lifecycle/main: clean scan independent of observer failure, cancellation, stale queued events, root replacement, retained retiring workers, preference failure/manual rescan, volume-only save without observer restart, and explicit observation-gap state all covered.
- Renderer: accessible Preferences/status controls, safe startup volume, dirty-state composition, rescan cancellation, stale preference recovery, revision/context guards and core-disconnect behavior implemented with RED/GREEN tests.
- Production Python/config frozen for the full supported sharded aggregate at 16:46 UTC; Node source now frozen for final real-core verification.
