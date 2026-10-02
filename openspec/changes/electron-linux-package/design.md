# Design

The existing Electron main path already expects resources/core/xfinaudio-core.
A PyInstaller 6.20.0 onedir build freezes the headless entry point and Python
interpreter using the hash-locked Qt-free requirements, explicitly excluding
Qt/desktop packages. Librosa lazy module/data and all locked dependency metadata
are collected. The frozen entry confines decoder PATH to _MEIPASS for M4A
audioread fallback without depending on a host engine. FFmpeg is placed at core/_internal/ffmpeg so the existing
frozen _MEIPASS resolver works without runtime code changes.

The assembly tool copies only Electron's distribution, generated .out, a minimal
app manifest, validated frozen core, and notices. It rejects unexpected symlinks,
Qt modules in the Python archive and Qt-named native libraries. Output must be
outside the source tree and never overwrite an existing destination.

FFmpeg 7.1.1 is built from official source with static internal libraries, no
network, no external codec libraries, and only required audio decoders/demuxers,
the null output and true-peak ebur128 filter. Source archive, SHA256, configuration
and license accompany provenance. This is loudness's existing analysis contract,
not a new audio editing pipeline. No privileges or sandbox disabling is required.

A clean PATH smoke relocates the package, validates JSONL requests over a real
subprocess with synthetic fixtures, and checks hash preservation for read-only
operations. Native UI QA is recorded separately. All caches/output/TMPDIR live
under /workspace; no project-root build/dist or additional /tmp pressure.

`runtime_bootstrap.py` validates the entire existing --data-dir CLI before writes,
then scopes NUMBA_CACHE_DIR and XDG_CACHE_HOME to the canonical data directory.
Numba's standard frozen-aware UserWideCacheLocator is selected explicitly because
its source-file-only locator rejects PyInstaller relative co_filenames. This uses
normal JIT and executable-hash invalidation without modifying algorithms or
Numba/librosa code. LIBROSA_CACHE_DIR is removed to preserve its disabled Joblib
cache default; noncanonical destinations/cache symlinks are rejected before mkdir.
