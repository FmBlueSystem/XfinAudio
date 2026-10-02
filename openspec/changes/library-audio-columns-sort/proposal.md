# Library audio details and sortable columns
Expose verified stream format, codec and bitrate in Library; make every real data column sortable by keyboard and mouse. Never infer encoding from filename, label a variable bitrate as fixed, mutate audio, reorder recommendation inputs, or persist display order. Old database rows remain valid with unavailable stream fields until a rescan.

Review budget: explicit chained implementation plan, each slice reviewed below 400 changed production/test lines: (1) stream metadata reader/model/persistence and fixture tests; (2) DTO and global sort/security tests; (3) headers, shared sort state and whole-app regressions; (4) explicit legacy schema-5/6/7 import compatibility and its security/source-preservation regressions. Documentation accompanies the chain. Final integration and aggregate gate belong to coordinator; no PR/release/build authorized here.

Risks: legacy schema, ambiguous MP4 codecs and declared ALAC bitrate, stale query replies, conflicting sort controls. Rollback uses previous source plus backed-up app database; schema upgrade is additive but older releases reject newer schema.

Success: real generated FLAC, MP3, WAV, AIFF, AAC/MP4, ALAC/MP4 survive read-only scan, restart and DTO; missing data is explicit. Entire filtered dataset sorts numerically/textually in both directions, nulls last. Existing filters, preview, selection and recommendation inputs remain intact.
