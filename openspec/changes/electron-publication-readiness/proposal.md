# Electron source-publication readiness

Prepare a separate 2.2.0 beta/source candidate from immutable V12. Synchronize version metadata, make CI exercise the supported full-manifest Python gate and every Electron test with a locked Qt-free interpreter, document dependency provenance and a reviewable publication chain. This is preparation only: no GitHub writes, merge, tag, release, binary publication, installed-app replacement or Mac candidate rebuild.

V12 source seal and its local Mac candidate remain unchanged. The existing PR360 and independent watcher branch are separate work; no commit from either is rewritten. Parent coordination is required for eventual publication. Source-only readiness and binary redistribution review remain separate.

This migration exceeds the 400-line review budget. Follow the explicit feature-branch chain in `publication-plan.md`; do not create dummy commits or pretend the full integration is a small review. This follow-up has separate metadata/docs, CI implementation/tests and dependency-inventory units. Split any unit that exceeds the budget into coherent review slices; a source integration draft is only the chain overview and is not ready to merge.

Success: versions agree at 2.2.0; no runtime/engine behavior changes; CI fails on test failure or skipped Electron cases, preserves complete collection/coverage89 and artifact evidence; full final source gates pass; source/binary/acceptance limitations remain explicit.
