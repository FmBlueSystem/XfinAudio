# Apply progress

2026-09-30: Proposal/spec/design/tasks complete before implementation. RED pending.

Slice 1 RED: integrated completion failed on stale dirty state and uncaught
FileNotFoundError; resume regression also failed with FileNotFoundError.
GREEN: 68 focused scan/watch/folder/MainWindow tests passed (3.87s).
Publication now goes through current-state/set-state accessors. Watcher failures
leave monitoring off and display manual-refresh guidance.

Slice 2 RED: all five slow-close subprocesses failed (including Qt abort), and
both AI cancel tests demonstrated a blocking wait. GREEN implementation defers
close on a 50ms Qt timer, requests cancellation without waiting, invalidates stale
completion, and retains replaced worker wrappers through thread destruction.
Initial stress run exposed a wrapper cleanup race; retention was extended beyond
finished emission to deferred Qt destruction before repeating verification.

Slice 3 RED: three analysis shutdown spies observed terminate/wait; loudness
shutdown blocked; slow spectral/loudness close subprocesses also failed. Repeated
start lost running ownership; replacement scan canceled its new token; geometry
save failure escaped closeEvent. GREEN: cooperative asynchronous drain, sibling
thread ownership visible to the shell, deferred wrapper retention, terminal-only
finished signals, guarded downstream stages, and recoverable geometry failure.
10 subprocess close cases pass; 63 focused regressions passed before final sweep.
No desktop terminate calls remain. UI cancellation controls/optimizer changes are
outside this lifecycle slice. Full integration gate remains parent-owned.
Final focused sweep: 294 passed; 1 known baseline UX-only test left to integration.
Final static checks: pyright 0 errors/0 warnings; ruff check/format pass.
