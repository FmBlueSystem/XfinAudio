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

Slice 5: RED absent readiness/ranking module; GREEN 4 pure-engine tests. Live
recomputes all adjacencies, requires zero readiness concerns, preserves the exact
pool and constraints, and ranks actual scores. No position-derived score remains
in the new engine contract. The screen integration follows in slice 6.

Slice 6: RED 3 missing/unsafe session behaviors; GREEN 31 Live pure/widget/window
smoke tests using temporary HOME. Raw library candidate bypass now fails closed.
Real mouse click proves engine-ranked selection, history, duplicate/stale rejection;
periodic identical context preserves the manual session, invalid context clears it.
The four legacy tests that opened unvalidated candidates now supply a ready set.

Slice 7a: RED missing replacement helper and UI action; GREEN 34 Review pure/widget
tests. Real table+button mouse interaction previews original/proposed scores and
readiness, protects locked/manual/start/end tracks, excludes forbidden candidates,
passes current loudness/scoring and preserves generation policy. No apply action.

Slice 7b: RED empty/oversized provider replies and rich-text rendering; GREEN
71 narrator/controller/Review tests. Replies are bounded to 150 words/2400 chars,
empty output is retryable, and HTML remains literal PlainText. Success explicitly
labels generated commentary for checking against authoritative local facts.

Corrective slice: RED wrong-origin/arc-history Live ranking; GREEN 5 pure tests.
Start track and arc sequence now remain bound even against direct invalid calls.
Focused pyright with the explicit shared-venv python path is clean; a nullable
QTableWidgetItem test assertion was made explicit for the widget overload.

Final focused verification: 143 tests pass, pyright 0 errors/warnings, Ruff lint
and format pass on all 13 touched Python files. Additional real controller/widget
interactions cover disabled-service Configure AI, injected retry, Cancel and set
switch. Integration/full release gate is explicitly left to the coordinator.
