# Apply progress

2026-10-02: Isolated V14 from immutable published V13. Hosted run 36947958552 failed immediately with no jobs at a79ad236. GitHub's official context table excludes runner from job-level env and permits it in step env; the local V13 suite had not tested that platform boundary.

RED: the new regression failed on the existing job-level runner.temp reference. GREEN: the binding moved to the actual Electron test step, preserving the exact isolated interpreter path; 47 focused CI/workflow/action-pin/sharding checks passed. Ruff check/format and targeted Pyright passed with the pinned legacy test environment. Every other workflow byte is unchanged. The two behavioral files total 17 changed lines. No application or packaging code changed.

The source is frozen for a fresh complete local aggregate and Electron run. The small correction may be published as a draft CI fix so GitHub can validate its own configuration; no green or merge-ready claim applies until exact-head hosted checks and matching local verification pass. Retain the initial failed run and distinguish it from the correction's evidence.
