# Feature: distribution-serato (Plan 3 — Features)

## Problem
The DMG is unsigned and un-notarized (packaging-strategy.md defers signing for local
builds): Gatekeeper blocks first launch on any machine that is not the developer's —
the single biggest distribution blocker. The Serato integration (the product's
differentiator) is currently one-directional: XfinAudio writes crates/loudness tags,
but never learns from Serato's own data (play history, existing crates).

## Goal
A DJ who is not the developer installs with a double click, and the recommender can
learn from what the DJ actually played/exported.

## Tasks
- [x] T1 — Signing/notarization: Developer ID + hardened runtime + notarytool wired into
      scripts/build_dmg.sh (gated on credentials being available; document prerequisites).
      Commit `89e4da8`. Credential-gated: XFINAUDIO_SIGN_IDENTITY / auto-detect of exactly
      one Developer ID Application identity / XFINAUDIO_NOTARY_PROFILE; unsigned default
      behavior preserved byte-for-byte (verified under bash 5 AND stock bash 3.2 — an
      earlier draft used mapfile and aborted on macOS's own bash, caught by verification).
      REAL signing still requires the user's Apple Developer account ($99/yr) + cert +
      notary profile; wired paths are pin-tested but never exercised with credentials.
- [x] T2 — Serato read integration: DONE. Commit `5305fcc`. Copy-then-parse reader
      (serato_history.py): V2 typed decoder, unknown-tolerance, depth cap, overlap-proof
      scratch guard (adversarially verified: 3 overlap shapes, deep nesting, timestamp
      range); SYNTHETIC fixtures (tags unverified against live sample — pending);
      settings flag default off. Aggregation deferred to T3.
- [x] T3 — Preference signal: DONE. Commit `6608a59`. FamiliaritySignal aggregate (play_count/latest/crate_count) + ScoringWeights.familiarity=0.0 (outside SCORED_COMPONENTS, inert) + candidate-pool rank-fraction boost capped 5%, reorder-only, NaN-safe inert gate. End-to-end enablement (desktop wiring) recorded as the T3 follow-up.
      history (design + safe default off).
- [x] T4 — Explainability in Review: DONE. Commit `a32fda6`. Per-track "why" tooltips (position, opener/closer role, metadata completeness with missing fields, adjacent-transition warnings) + "Energy arc X→Y" in the readiness summary. DjReadinessReport proved playlist-level only — no per-track readiness invented; follow-up: metadata check should emit affected paths. Signature-staleness risk bounded theoretical by the verifier.
      per included/excluded track in the UI (no JSON reading).
- [ ] T5 — Work-unit commits per slice; record hashes below.

## Evidence
- (pending) per-slice commit hashes.

## Checks
- [ ] DMG passes codesign --verify --strict and notarytool returns Accepted.
- [ ] Serato read path provably never mutates Serato files (existing security invariant).
