# Focused verification

- RED: new first-Play regression failed with actual IDLE versus expected PLAYING.
- GREEN: 61 tests passed across preview lifecycle, Library preview/screen and path index.
- Targeted Ruff lint/format passed; targeted Pyright passed using the existing venv
  explicitly via --pythonpath (the worktree has no separate installed environment).
- Regression checks every original item identity, selected paths, preview icon,
  continued playback and a subsequent full shell state sync. Invalid content cache
  is retained rather than eagerly rebuilding or incorrectly marking rows current.

No real audio, user library, native macOS or AX bridge was exercised. This does not
claim to fix the reported native crash. Parent owns aggregate/native verification.
