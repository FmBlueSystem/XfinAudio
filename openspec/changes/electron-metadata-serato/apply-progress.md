# Implementation checkpoint

- RED: four new backend cases failed on the absent metadata selector; three renderer cases failed on the missing callback/source union.
- GREEN: exact complete/incomplete/missing-field scope uses existing pure Serato metadata planners through the existing preview, native confirmation, direct selected destination, validation and backup writer.
- Backend rejects empty/over500/duplicate/unknown/mismatched/malformed scope; source changes invalidate confirmation. The warning explicitly says this is a metadata worklist rather than DJ readiness.
- Renderer exports the whole filtered gap set across pages, refuses0/>500 rather than truncating, and defensively copies opaque IDs. Shared IPC and app route wiring is integrated by the UI owner, including guarded callbacks and truthful source labels.
- Only temporary synthetic files and app-owned databases/Serato sentinels were used. No original audio, database V2 or live Serato was changed.
