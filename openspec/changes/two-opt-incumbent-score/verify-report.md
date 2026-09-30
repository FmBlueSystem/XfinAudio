# Verification

- Recovery RED: one operation-count failure; 30 calls versus at most 16 (`two-opt-recovery-red.log`).
- GREEN: 212 focused tests passed in 81.22 s across incumbent scoring, sequence optimization, unchanged performance thresholds, Live Assistant and MainWindow (`algorithm-recovery-green.log`).
- Ruff check and formatting pass for the changed Python files.
- The current integration release gate is pending. Focused success does not establish native macOS or real audio/Serato validation.

Tests run with an isolated writable HOME and Qt offscreen. An initial recovery attempt used the default read-only HOME and failed fixture setup; rerunning with the documented isolated HOME resolves that environment issue.
