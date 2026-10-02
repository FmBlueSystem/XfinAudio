# Audit release provenance

## Intent and scope
Enforce the documented exact-commit non-audio gate before local DMG packaging,
including reuse of an existing app. Bind successful builds to source SHA, project
version, and a content manifest. Pin workflow actions to official immutable
commits and remove the unused FFmpeg signature download without weakening its
pinned archive checksum.

Out: algorithm/UI changes, live audio or Serato, native macOS builds, credentials,
signing/notarization execution, publishing, push, PR, merge, or deploy.

## Success, risks, rollback
Packaging fails before build/reuse after a dirty checkout or failed gate; reuse
fails without matching source/version/content evidence. Successful fresh builds
produce reusable evidence. Optional signing/notarization remains unchanged.
Synthetic Linux tests prove orchestration, not real macOS compatibility.
Rollback by reverting local commits; never relax the documented release gate.
Local evidence detects accidental stale/tampered bundles, not a malicious local
user who can rewrite both code and evidence. Dependencies/toolchains and ignored
FFmpeg input are not claimed hermetic or independently attested.

## Explicit review chain
The aggregate change may exceed 400 lines. Deliver local conventional commits
as independently reviewable slices (each at most 400 changed lines):
1. SDD plan and provenance-helper RED/GREEN cycle.
2. Packaging-orchestration RED/GREEN cycle and operational documentation.
3. Immutable action references and FFmpeg checksum-only clarity, with RED/GREEN.
4. Verification evidence and any narrowly scoped test-driven hardening.
Parent owns the final integrated exact-HEAD gate; no remote PRs are created.
