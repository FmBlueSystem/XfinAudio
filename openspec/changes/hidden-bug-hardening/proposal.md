# Proposal: Hidden Bug Hardening

## Summary

Fix hidden state, enrichment, provider cache, and BPM sequencing defects discovered during live app QA and parallel code audit.

## Scope

- Recommendation sequencing must not fail or discard valid tracks because BPM pruning runs before optimization.
- Desktop UI state must not retain stale selections or constraints across filters/folder changes.
- Genre enrichment settings must be honored by services, repositories, and desktop scan wiring.
- Runtime provider transient failures must not be cached as permanent empty results.

## Non-Goals

- No audio mutation.
- No DSP expansion.
- No live Serato DB V2 writes.
- No new provider data committed to repo assets.
