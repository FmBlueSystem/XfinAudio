# Linux x86_64 self-contained Electron runtime

This is a portable folder/tarball, not a system installer. The included `xfinaudio`
ELF launches Electron; `resources/core/xfinaudio-core` embeds CPython and the
Qt-free application dependencies. `_internal/ffmpeg` embeds FFmpeg's audio
libraries. No system Python, pip, npm, Node or FFmpeg is needed to use it.
The original native confirmations and read-only/default-disabled AI boundaries
are unchanged. There is no updater, signing, publishing or privilege change.

## Supported baseline and limits

The candidate is built and tested on Debian 13 x86_64 with glibc 2.41. It still
requires ordinary Linux graphical desktop libraries (GTK/NSS/X11 or Wayland),
a session/audio service, and functioning Chromium sandbox support. Do not infer
compatibility with older distributions, ARM, macOS or Windows. Do not add
`--no-sandbox`, change sandbox permissions, or run this app as root to bypass a
host limitation. A frozen-core smoke is not a graphical launch test.

## Reproducible inputs

- Electron 44.5.1 from the existing npm lock; TypeScript UI built locally
- Python runtime dependencies from `desktop-electron/requirements-headless.txt`
- Freezer toolchain from `requirements-build.txt`, installed with `--require-hashes`.
  Regenerate it with `uv pip compile --generate-hashes --python-platform linux
  requirements-build.in -o requirements-build.txt`; the platform flag is what keeps the
  Darwin-only `macholib` pin out of this lock, and
  `tests/test_headless_requirements_lock_drift.py` fails if the compiled file stops
  matching `desktop-electron/requirements-headless.txt`
- FFmpeg 7.1.1 from `ffmpeg-source.json` (official HTTPS source and pinned SHA256)
- `ffmpeg-configure.args` uses static FFmpeg libraries, no networking/external codec
  libraries, required AIFF/FLAC/MP3/M4A/WAV decoders and true-peak EBU R128; raw PCM
  output supports audioread M4A fallback and unchanged decoded-sample verification

The FFmpeg executable is allowed to depend only on the declared host C/math/ELF
loader baseline. No host libav* or external codec package is accepted. Version,
demuxers, decoders, true-peak support, and dynamic dependencies are checked before
packaging. LGPL source, build flags, license, and exact binary hash are retained.

## Build workflow

Use an external build workspace with sufficient capacity and point TMPDIR and
UV_CACHE_DIR there. Never create root `build/` or `dist/`. Install a clean freezer
environment using the hash-locked build requirements; do not install this
repository's legacy Qt-bearing pyproject dependencies into it.

Download the official source URL, verify the pinned SHA256, extract with a safe
archive filter, and run its configure with the literal lines in
`ffmpeg-configure.args`, followed by `make -j4`. Do not change the flags without
updating tests and re-verifying format/true-peak behavior.

Run the full repository release aggregate on the exact final source. The verifier
must record `packaging/linux/build.py:source_digest(root)` before and after it and
append the identical value as `source_sha256` to the successful report. All named
gates and root hygiene must pass. Also run every Electron test with the real
Qt-free runtime so integration tests are not silently skipped; append an
`electron_tests` object containing `status: "passed"`, the actual `passed` count,
and `failed: 0`, `skipped: 0` to the sealed report. Preserve the raw
evidence; do not manufacture a passed report or reduce the coverage floor.

Run the clean freezer's Python with:

```
packaging/linux/build.py --root SOURCE --output NEW_EXTERNAL_WORKSPACE \
  --gate-report SEALED_REPORT.json --ffmpeg OFFICIAL_SOURCE_BUILD/ffmpeg \
  --ffmpeg-source ffmpeg-7.1.1.tar.xz
```

The output path must not exist. Source seals are rechecked around compilation
and assembly. The package's module inventory rejects Qt/retired desktop modules;
The freezer explicitly collects SciPy 1.18's dynamically imported vendored NumPy
FFT/linalg modules, and directs its build cache into the output workspace. The
file audits reject Qt libraries, development node_modules and non-relocatable
symlinks. Python/package licenses are collected with their distribution metadata.
The tarball has a SHA256 sidecar and full build provenance.

Before importing the headless runtime, the frozen bootstrap validates the complete
`--data-dir` CLI and canonical destination. JIT code cache lives only below that
directory's `cache/numba`; child XDG cache and Numba's built-in frozen-aware
`UserWideCacheLocator` are bound there too. Hostile inherited cache/locator values
are overridden. Inherited `LIBROSA_CACHE_DIR` is cleared, preserving librosa's
disabled Joblib waveform/array cache default. Cache symlink escapes and malformed
arguments fail before cache directory creation. Development startup is unchanged.

## Runtime verification

Execute `smoke.mjs` with the **included Electron** in Node mode:

```
ELECTRON_RUN_AS_NODE=1 BUNDLE/xfinaudio packaging/linux/smoke.mjs \
  BUNDLE desktop-electron/tests/fixtures/music NEW_EXTERNAL_EVIDENCE_DIR \
  SYNTHETIC_PROFILE_FIXTURES
```

The script copies the bundle to a path with spaces, temporarily hides the original
bundle to prevent fallback, and restores it in `finally`. The frozen core and
bundled FFmpeg receive an empty PATH and isolated HOME/config. Only synthetic
fixtures are used. Evidence covers scan/metadata, Prep, Live, editor persistence,
preferences restart, offline AI defaults, unchanged source hashes, and a copied metadata-tagged
65-second synthetic tone: refusal before confirmation, actual tag write, byte-exact backup,
identical decoded PCM, and repeat-cache no-write behavior. The separate profile
fixture directory must contain generated, metadata-tagged 65-second tone.wav, tone.flac, tone.mp3,
tone.aac.m4a, tone.alac.m4a and tone.aiff. These exercise all three original
read-only analyzers, persisted cache reuse after restart, M4A audioread fallback
through only bundled FFmpeg, and unchanged source hashes. Generate these only on
the build/QA machine from synthetic PCM; no user audio or remote media is needed.
The original metadata-first scanner deliberately skips audio with no tag container.
Prepare tagged copies with the clean freezer Python (which includes Mutagen):

```
python packaging/linux/prepare_smoke_fixtures.py SIX_SYNTHETIC_INPUTS \
  NEW_TAGGED_FIXTURE_DIRECTORY BUNDLE/resources/core/_internal/ffmpeg
```

Use that new directory as `SYNTHETIC_PROFILE_FIXTURES`. The preparation helper
copies all six files, adds a synthetic title, and verifies unchanged input hashes
and decoded PCM. Its `fixture-preparation.json` records those assertions. It is
only for disposable synthetic QA inputs; do not point it at a real music library.

Separately launch the actual `xfinaudio` executable in a supported graphical
session with sandbox enabled. Record success or the exact host blocker. Electron
Node-mode and JSONL tests do not establish GUI startup, desktop playback, or
native-dialog usability. Deliver matching GPL application source alongside the
candidate, with this bundle's source digest and third-party notices. Do not
publish or call it a release until all release requirements are met.
