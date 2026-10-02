# Requirements

R1: GIVEN authorized Library metadata WHEN an explicit English/Spanish request is interpreted THEN existing offline interpretation applies supported genre/BPM/key/energy/title constraints, returns editable values, and rejects unsupported words visibly. Manual ranges reject inverted bounds and exclude unknown values.

R2: GIVEN a Library query WHEN sorting or hiding duplicates THEN only the view changes, numeric values sort numerically, absent values stay last, and the original conservative grouping and representative rules apply. No record or source file changes.

R3: GIVEN saved sets WHEN local search or a selection comparison is requested THEN the original neutral search/comparison evidence is returned without provider access. Comparison requires 2–200 distinct existing IDs.

R4: GIVEN a saved set WHEN removal is requested THEN native confirmation names the exact set and track count, cancellation writes nothing, and commit requires its exact revision and one-use preview identity. Changed snapshots fail closed.

R5: GIVEN confirmed removal WHEN the atomic transaction succeeds THEN the complete ordered references and name survive in app-owned recovery storage and the set disappears from active lists. Failed archival leaves the original intact. Recovery is visible after process restart and restores references without touching audio or other sets. Repeated restore cannot duplicate content.

R6: GIVEN any renderer request WHEN validation or operation fails THEN private paths and raw exceptions remain hidden; renderer cannot provide a filesystem path or confirmation boolean. Busy/closing/stale responses cannot publish an outdated view.
