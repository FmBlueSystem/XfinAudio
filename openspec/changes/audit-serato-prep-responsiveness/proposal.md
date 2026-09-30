# Responsive preparation and keyboard-visible review

## Intent
Complete the remaining shared-core F7/F8 audit work after the A–E correctness tranche passes its integrated gate. Only Serato/shared UX is in scope. Existing metadata, DSP, optimizer and loudness semantics stay unchanged.

## Scope and success
Prep generation runs outside the GUI thread with visible busy/progress/cancel state. Cancellation, failure and superseded completions preserve the last successful plan and applied recommendation. Keyboard selection exposes Review transition explanations without hover.

## Risks and rollback
Use the existing retained-worker/request-ID lifecycle and asynchronous close draining. Snapshot UI-derived inputs before worker execution; never access Qt widgets from background code. Cancellation is cooperative; a running bounded stage may drain, while stale results are discarded. Revert each slice independently if needed.

## Chained delivery
Expected total exceeds 400 changed lines; explicit feature-branch chained-PR plan, local commits only:
1. G1: asynchronous Prep request/result boundary and immutable busy state, with heartbeat/thread-lifetime tests
2. G2: cooperative cancellation/progress and preserve-last-result contract, with cancel/retry/close tests
3. H1: selection-driven Review detail panel, keyboard and compact-layout regressions
4. I1: Serato destination guidance, only after resolving actual crate destination versus report-folder semantics

No push, PR, deployment, real audio, real Serato import or live database writes are authorized by these implementation steps.
