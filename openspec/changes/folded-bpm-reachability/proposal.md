# Folded BPM reachability

## Intent and scope
The pool prefilter currently partitions consecutive sorted BPM values, although
its comparator accepts nonlocal half/double-time edges. An unrelated 90 BPM
record therefore hides the valid 60-to-120 edge. Correct only this prefilter and
add focused tests; preserve sequencing, controls, scoring, and metadata.

## Success, risks, rollback
Return the actual anchor component (or deterministic largest component without
a measurable anchor), retaining protected and unknown-BPM tracks as before.
Avoid eager all-pairs graphs. Verify against an independent small all-pairs BFS
and the public recommendation path. Floating-point window boundaries and dense
libraries are the main risks. Revert this isolated commit to roll back.
No DSP, audio writes, live Serato changes, dependencies, push, or deployment.
This slice targets fewer than 400 changed lines, including its SDD artifacts.
