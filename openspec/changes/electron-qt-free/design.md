# Design

Electron main owns native folder selection, process lifecycle, a fixed IPC allowlist, request validation and authorization. Sandboxed context-isolated renderer has no Node and receives only data/opaque track IDs through a narrow preload. Local xfin-app assets have strict CSP; network/navigation/window creation/permissions are denied. No HTTP listening port. Audio is streamed by authorized opaque ID under xfin-audio with single byte-range validation, realpath confinement and correct 206/416/HEAD semantics.

Python is launched via an explicit developer interpreter or, later, a bundled executable. JSON lines over stdin/stdout carry bounded schema-validated requests, replies and progress with IDs. Logs use stderr. App-owned isolated data directory contains library/playlist databases. No desktop composition roots, provider calls, loudness completion or live Serato paths are loaded. Existing workflow/repository/Prep services supply all algorithms. Backend work is serial with cancellation; renderer and host reject stale IDs. No credentials or arbitrary shell/process commands cross the bridge.

New code lives in src/xfinaudio/headless and desktop-electron. Build output is desktop-electron/.out, never project-root build/dist. The existing Qt app is not changed or claimed fixed.
