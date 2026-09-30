# Apply progress

2026-09-30: proposal, specification, design and tasks complete before code.
All tests use synthetic metadata and injected network seams. No real API keys.

Slice 2: RED reproduced 5 stale/queued/cancel failures; GREEN 22 narrator tests.
Identity is validated on the UI thread after queued delivery; cancel immediately
releases loading and permits retry while WorkerRegistry retains old workers.

Slice 3a: RED reproduced missing numeric transition explanations and path fallback
transmission; GREEN 15 injected-transport narrator tests. Facts now include existing
scores/explanations/readiness checks; paths are redacted including warning text.

Slice 3b: RED absent local-facts module; GREEN 3 pure tests. Comparisons use only
an engine Prep plan containing the exact applied recommendation, omit conflicts
with current locks/exclusions, and compare normalized scores plus readiness.

Slice 4: RED missing widget actions; GREEN 28 Review widget tests including real
QTest mouse clicks for Configure AI, Cancel and offline local facts. Facts panel is
opt-in/collapsible so idle Review retains its table space.
