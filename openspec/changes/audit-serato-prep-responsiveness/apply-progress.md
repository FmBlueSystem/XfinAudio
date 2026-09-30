# Apply progress

2026-09-30: proposal/spec/design/tasks prepared only. No production implementation or new behavior tests applied. Waiting for the preceding integrated gate and parent confirmation. I1 also awaits destination-semantics decision.

2026-09-30: parent explicitly authorized independent G1/G2/H1 Apply while the integration owner resolves five algorithm-related gate failures. Rebased onto 03b0ce7 with retained-worker lifecycle. I1 remains blocked; no Serato destination behavior changes.

G1 RED: MainWindow generation blocked the GUI for the synthetic 400ms builder; failing builders raised through the UI call. GREEN: desktop injects a retained QObject/QThread task runner into the existing synchronous coordinator seam; all UI inputs and candidate routes capture a library snapshot first. Background result signals publish on the GUI thread and failures keep the previous plan. Busy state disables duplicate generation, and close drains the retained worker. REFACTOR removed the old state-reading pool-note helper. Existing coordinator unit tests remain synchronous through their injected boundary; MainWindow tests now wait for actual async completion/cleanup. VERIFY: 77 focused Prep/Build tests and 9 of 10 MainWindow Prep tests pass; the remaining readiness expectation is the already-owned algorithm regression from the integration gate.
