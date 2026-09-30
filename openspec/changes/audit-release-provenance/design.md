# Design

A small standard-library script owns clean Git SHA validation, TOML version
reading, deterministic file/type/mode/symlink manifest hashing, and JSON
sidecar creation/validation. Its sidecar sits outside the app so signing is not
invalidated by evidence. Internal symlinks are hashed without traversal; unsafe
external/broken links and special files fail closed. Atomic sidecar replacement
avoids accepting a partially written manifest.

The shell orchestrator normalizes the output path before changing directories,
checks clean SHA, runs `release_gate_check.py --run`, and rechecks that SHA.
Both new and reused bundles go through this gate. Reuse verifies provenance
before any signing/smoke; a successful fresh build or authorized re-sign is
recorded after signing/smoke. The staged copy must match that digest before image
creation. Source is rechecked around boundaries. No report from another commit
or previous run bypasses execution of the gate.

Version is read by TOML parser from `[project]`, not the first textual version.
The existing PyInstaller, signing, notarization, and image tooling remains;
synthetic executables exercise the actual shell pipeline on Linux.

No dependencies, public application APIs, or AppState changes. Relevant files:
`scripts/build_dmg.sh`, new provenance helper/tests, workflow references,
`scripts/build_ffmpeg_universal.py` and its tests, release documentation.

Official action releases verified on 2026-09-30 (retain same major versions):
- actions/checkout v4.3.1: https://github.com/actions/checkout/commit/34e114876b0b11c390a56381ad16ebd13914f8d5
- actions/setup-python v5.6.0: https://github.com/actions/setup-python/commit/a26af69be951a213d495a4c3e4e4022e16d87065
- astral-sh/setup-uv v6.8.0: https://github.com/astral-sh/setup-uv/commit/d0cc045d04ccac9d8b7881df0226f9e82c39688e
- actions/upload-artifact v4.6.2: https://github.com/actions/upload-artifact/commit/ea165f8d65b6e75b540449e92b4886f43607fa02
These pins constrain retargetable tags, not a guarantee of bug-free third-party code.
