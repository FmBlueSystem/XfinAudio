# Serato Recommendation Export Specification

## Purpose

Define the observable behavior required so a successful Serato crate write is
never reported, recorded, or resolved as a failure when only readiness-sidecar
generation fails afterward, and so the export dependency bundle
(`ExportDependencies`) exposes only consumed, statically-typed collaborators.
This is a delta over the existing `serato-recommendation-export` capability:
it broadens the sidecar-failure boundary to be uniform across exception types
and removes two readability liabilities in the dependency bundle. It does not
change the crate-writing path, the readiness-report content, the sidecar file
format, or the export-history schema.

## Requirements

### Requirement: Crate Write Success Is Independent of Sidecar Outcome

`export_recommendation_to_serato` MUST treat a successful Serato crate write as
final and complete regardless of whether the subsequent readiness-sidecar
generation step (`write_readiness_sidecars`) succeeds, raises `OSError`, or
raises any other exception.

#### Scenario: Sidecar generation raises a non-OSError exception after crate write

- GIVEN a Serato crate write has already completed successfully and is present
  on disk at `result.written_path`
- WHEN `write_readiness_sidecars` raises an exception that is not an `OSError`
  (for example a `ValueError`, `RuntimeError`, or a domain-specific error from
  the readiness writer)
- THEN the crate at `result.written_path` MUST remain unchanged and present on
  disk
- AND the exception MUST NOT propagate out of `export_recommendation_to_serato`
- AND the export MUST be reported through the same degraded-success path
  already used for an `OSError` sidecar failure, rather than as a hard export
  failure.

#### Scenario: Sidecar generation succeeds

- GIVEN a Serato crate write has completed successfully
- WHEN `write_readiness_sidecars` returns both a JSON and CSV path without
  raising
- THEN behavior MUST remain exactly as it is today: both readiness paths are
  reported and recorded, and the success callback runs (subject to the
  existing readiness-quality gates unrelated to this change).

### Requirement: Partial Success Is Surfaced In The Export UI

When a crate write succeeds but readiness-sidecar generation fails for any
reason, the export guidance label and the status text MUST both report the
successful crate path and the sidecar failure, using the same rendering
already applied to the `OSError` case.

#### Scenario: UI reports crate path and sidecar failure together

- GIVEN a Serato crate write succeeded and sidecar generation subsequently
  failed (`OSError` or any other exception)
- WHEN `export_recommendation_to_serato` finishes handling the export
- THEN `export_guidance_label` text MUST include the written crate path
- AND `export_guidance_label` text MUST include a sidecar-failure note
- AND `status_label` text MUST include the written crate path
- AND `status_label` text MUST include a sidecar-failure indication
- AND the failure MUST be logged via `LOGGER.exception` so the underlying
  cause remains diagnosable.

### Requirement: Export History Records The Partial-Success Receipt

`_record_serato_export` MUST be invoked after any sidecar failure that follows
a successful crate write, recording a receipt with the crate path present and
the readiness JSON/CSV paths absent.

#### Scenario: History receipt reflects partial success

- GIVEN a Serato crate write succeeded and sidecar generation failed for any
  reason after that write
- WHEN the export flow completes
- THEN `_record_serato_export` MUST be called with `written_path` set to the
  successful crate path
- AND `readiness_json_path` MUST be `None`
- AND `readiness_csv_path` MUST be `None`
- AND the resulting entry MUST appear in `host.serato_export_history` bounded
  by the existing history limit, identically to how the `OSError` case is
  recorded today.

### Requirement: Success-Callback Policy On Partial Success Is Explicit And Test-Covered

The success callback (`self._on_export_success`) MUST be suppressed whenever a
Serato export finishes in the partial-success state (crate written, sidecar
generation failed for any reason), matching the callback-suppression behavior
already implemented for the `OSError` sidecar failure. This policy MUST be
asserted directly by an automated test, not left as an incidental side effect
of unrelated assertions.

#### Scenario: Callback is suppressed for any sidecar failure

- GIVEN a Serato crate write succeeded and sidecar generation failed
  (`OSError` or any other exception) while a readiness report was available
- WHEN `export_recommendation_to_serato` completes
- THEN `self._on_export_success` MUST NOT be invoked
- AND a dedicated test MUST assert this non-invocation for a non-`OSError`
  failure, in addition to the existing `OSError` coverage.

#### Scenario: Callback still runs when sidecar generation succeeds

- GIVEN a Serato crate write succeeded and sidecar generation also succeeded
  (or no readiness report was available to attempt sidecar generation)
- WHEN `export_recommendation_to_serato` completes
- THEN `self._on_export_success` MUST be invoked exactly as it is today,
  unaffected by this change.

### Requirement: Sidecar Retry Never Rewrites Or Corrupts The Crate

Retrying readiness-sidecar generation after a partial-success export MUST NOT
re-enter, rewrite, or otherwise mutate the already-written Serato crate.

#### Scenario: Retried sidecar generation leaves the crate untouched

- GIVEN a Serato crate was written successfully and the subsequent sidecar
  attempt failed, producing a partial-success outcome
- WHEN readiness-sidecar generation is retried (manually or by any future
  retry path) using the same crate path
- THEN the crate file's content and modification identity MUST be unaffected
  by the retry
- AND no code path exercised by the retry MUST call the crate-writing routine
  again.

### Requirement: Export Dependency Bundle Exposes Only Consumed Collaborators

`ExportDependencies` MUST declare only collaborators that are actually invoked
through the bundle by at least one consumer; a collaborator accessed exclusively
via a direct module import MUST NOT also be duplicated as an unused bundle
field.

#### Scenario: Unused bundle field is removed

- GIVEN `write_application_dj_readiness_report` is never called through
  `dependencies.write_application_dj_readiness_report` anywhere in the
  codebase, and `export_actions.py` imports the function directly instead
- WHEN `ExportDependencies` and `default_export_dependencies` are inspected
- THEN `ExportDependencies` MUST NOT declare a
  `write_application_dj_readiness_report` field
- AND the direct import in `export_actions.py` MUST continue to work
  unchanged
- AND every remaining field on `ExportDependencies` MUST have at least one
  bundle-mediated caller (`dependencies.<field>(...)`) in the codebase.

### Requirement: Export Dependency Collaborator Contracts Are Statically Typed

Every field on `ExportDependencies` MUST declare an explicit `Protocol` or
typed-alias contract matching its collaborator's real call signature and
return type; no field MAY be typed as `Callable[..., Any]`.

#### Scenario: Each collaborator has a checked contract

- GIVEN the `ExportDependencies` dataclass definition
- WHEN its fields are inspected
- THEN none of its fields MUST be typed `Callable[..., Any]`
- AND each field's type MUST be a `Protocol` or typed alias whose call
  signature matches the collaborator it is assigned in
  `default_export_dependencies` and in `ExportCoordinator._export_dependencies`
- AND `pyright` MUST report no new errors introduced by this change when
  checking `src` and `tests`.

#### Scenario: Behavior is unchanged by the typing migration

- GIVEN the typed contracts replace the previous `Callable[..., Any]` fields
- WHEN the existing Serato and export test suites run
- THEN all previously passing tests MUST continue to pass without
  modification to their assertions
- AND no runtime dispatch behavior of any collaborator MUST change as a
  result of the type migration.
