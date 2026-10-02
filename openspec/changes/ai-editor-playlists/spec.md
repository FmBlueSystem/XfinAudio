# Observable behavior

- GIVEN a saved set WHEN it is opened THEN its draft editor becomes visible via the shell hook.
- GIVEN an editor request to shorten to N tracks or N minutes WHEN previewed THEN a deterministic proposed order is shown without editing the draft or repository.
- GIVEN energy rise/fall ordering WHEN previewed THEN existing energy metadata alone determines unlocked ordering, missing energy rejects the request, and locked slots stay fixed.
- GIVEN locks/exclusions WHEN any proposal or Save is validated THEN locked membership is retained and excluded tracks cannot remain; contradictory controls are rejected.
- GIVEN a preview WHEN confirmed THEN only the draft changes; Save alone persists the validated draft.
- GIVEN manual edits, changed metadata/constraints, another opened playlist, or cancelled edits WHEN old confirmation is attempted THEN stale results cannot apply.
- GIVEN a dirty draft WHEN Cancel is clicked THEN the last saved snapshot is restored; export is disabled until Save or Cancel.
- GIVEN repository changes after opening WHEN Save is clicked THEN overwriting those changes is refused.
- GIVEN saved sets WHEN queried in natural language by name or compared by selection THEN output is derived only from those sets and known metadata, including explicit unknown coverage.
- GIVEN search/comparison WHEN run THEN no provider/network call or persistence occurs.
- GIVEN a conversational proposal WHEN previewed THEN existing transition scoring, quality and DJ readiness rules evaluate its exact order; hard blockers reject application, review warnings stay visible before confirmation.
- GIVEN unsaved changes WHEN another saved set is opened THEN the draft is preserved with a Save/discard instruction.
