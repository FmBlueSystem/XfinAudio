# Apply progress

2026-09-30: Read governance, inspected current Library/Create and established chain.
No implementation before SDD. Existing extraction sends titles; default transmission
will be narrowed. Existing controller generates immediately, so preview is a behavior
change and legacy lifecycle tests must explicitly confirm the new two-stage contract.

Slice 2 RED: test_library_query failed collection (new parser absent). GREEN:
9 parser/predicate cases pass with exact English/Spanish ranges, unsupported and
invalid constraints rejected, unknown metadata excluded, immutable records retained.

Slice 3 RED: both real-widget scenarios failed (query panel absent). GREEN: 11
parser/widget tests pass. QTest keyboard/clicks exercise local interpretation,
visible fields, edited range apply, invalid preservation, retry and clear.

Slice 3 follow-up: the initial 11 green assertions had a process-exit SIGSEGV,
not a clean pass; fixed the panel's owning-screen reference cycle using weakref.
Rerun exits 0. Real MainWindow callback RED exposed filter reset (2 rows vs 1).
GREEN keeps described filters and duplicate suppression through the callback;
12 focused tests now pass and process exits 0. Initial long-line lint fixed.

Correction: the first weakref text edit did not match formatted source. Applied
and inspected the actual replacement, removed import-sort lint, reran all 12
focused cases successfully. The screen no longer owns a callback closing over itself.

Slice 4 RED: real BuildScreen lacked confirmation signals. GREEN: QTest confirms
preview duration/style/constraints, edited duration, edit/cancel/configure signals
and unchecked per-request inventory consent; 2 widget tests pass.

Slice 5a RED: absent constraint merger. GREEN: 5 tests verify preservation of
selected order, locks/exclusions/start and fail-closed unknown/overlap/count inputs.
This is a separate <=400-line review slice before asynchronous controller changes.

Slice 5b RED: 5 actual-widget controller scenarios fail as expected: old code
plans before confirmation, lacks cancellation/retry wiring, accepts stale context,
and directs configuration failures to restart. Tests committed as the red boundary;
next linked slice implements the two-stage lifecycle.

Slice 5c GREEN: interpretation and local generation are separate workers with
mandatory visible confirmation, editable fields, cancel/retry, snapshot validity
checks before confirmation and publication, and queued request-ID checks. Existing
controller tests now explicitly confirm before expecting a plan; real QThread test
still proves extraction is off UI thread. 23 controller/workflow tests pass.
Candidate-route factory is an explicit coordinator integration hook.

Slice 6 RED: 9 tests expose default title transmission, missing opt-in flag,
untrusted path/metadata field acceptance, ambiguous title selection and raw error
echo. GREEN: 43 adapter/Create tests pass. Default payload contains request plus
genres; explicit title/genre opt-in never includes paths/audio/raw metadata. Strict
field allowlist rejects path or metadata injection. Raw provider errors no longer
echo model text. Ambiguous titles do not resolve arbitrarily.

Slice 7a RED: original conversational opening example failed parsing. GREEN:
14 Library tests pass, including actual widgets showing the documented gentle/
opening energy 2–5 suggestion, editable override and missing-energy exclusion.
The suggestion changes filters only; no track metadata is inferred or written.

Slice 7b RED: four added widget scenarios exposed concurrent-generator confirm,
busy-stage label reset, candidate routes retaining the wrong genre, and prompt
changes retaining an obsolete preview. GREEN: 28 lifecycle/controller cases pass.
Confirmation now binds candidate hard constraints and edited genre, waits for other
generation/scan, and snapshots request text. Per-request opt-in resets immediately.
Focused type-check also identified two test seam annotations, now corrected.
