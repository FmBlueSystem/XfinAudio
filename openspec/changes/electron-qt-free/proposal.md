# Qt-free desktop migration

Replace the failing Qt desktop presentation layer with Electron, local TypeScript views and a separate Python core process. Preserve the existing recommendation algorithms, read-only metadata scan, SQLite repositories and the existing Qt application as rollback. First slice: scan copied fixtures, generate balanced Prep, review, explicitly save/open playlists, preview FLAC play/pause/seek/switch. No provider calls, loudness tag writes, live Serato writes, public push or release in this slice.

Success means an independently runnable Qt-free prototype with tested protocol/security, real core workflows, and explicit limitations. Distribution must ultimately bundle Python; source development is not a distributable release.

## Chained review plan

The migration exceeds 400 lines. Review and eventually publish only as a feature-branch chain: (1) typed backend protocol + tests, (2) secure host and audio protocol + tests, (3) renderer workflows + tests, (4) Qt-free packaging and dependency split, (5) remaining screen parity. Each change is separately reviewable; split further to stay within the 400-line review budget. No publication is authorized yet.
