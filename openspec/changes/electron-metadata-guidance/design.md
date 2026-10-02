# Architecture

Move guidance logic unchanged to metadata/repair_guidance_core.py. Inject Callable[[str], str] translation with identity default; the existing repair_guidance.py becomes the Qt adapter and reexports the shared RepairPriority dataclass.

headless/metadata_report.py materializes the input once and calls metadata_gaps.build_metadata_gap_report plus the shared guidance functions. The public payload has totalTracks, completeCount, incompleteCount; gaps uses domain field names; yearCoverage has withReleaseYear/withoutReleaseYear; tracks contains incomplete entries sorted by path with id, title, artist, releaseYear, missingFields, explanation, locked and priority; repairPlan and readOnly complete the envelope. IDs are the same SHA256(path UTF-8) scheme used by the bridge. No path or raw metadata fields are returned. Display text remains metadata, with Untitled fallback, never a filesystem-derived name.

The integration slice wires backend commands and renderer; those files are outside this slice. No dependency changes or application state mutations are needed. Tests run in the separate Qt-free environment with --noconftest, and compatibility runs in the existing Qt environment.
