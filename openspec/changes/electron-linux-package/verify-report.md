# Verification status

## Passed before package build

- 38 packaging unit tests (strict preceding RED evidence retained externally)
- Ruff lint/format and explicit Pyright on packaging/test code
- Smoke integration script parses in Node
- Fresh freezer installation is Qt-free and exactly matches hash-locked V9 runtime
  plus PyInstaller 6.20.0 and its locked build dependencies
- FFmpeg source and executable SHA256 recorded; required format/filter validation
  passes on the real binary
- Six synthetic 65-second audio formats pass actual EBU R128 true-peak analysis
  with no executable available on PATH
- FFmpeg dynamic dependency audit is limited to Linux C/math/loader baseline

## Dependency-only frozen runtime passed

A tiny independent script (no XfinAudio imports) froze the real dependencies and
executed librosa load/STFT/mel/centroid/bandwidth/rolloff/onset/autocorrelation/
tempogram/HPSS and intro/outro loads across six 65-second synthetic formats.
Cold and warm runs pass, including AAC/ALAC M4A audioread fallback. The bundle was
relocated to a path with spaces and made read-only; initial PATH was empty.
Source SHA256 and mtimes are unchanged. All 52 Numba cache files stayed in
isolated writable test data and were reused unchanged on the warm run. The
2,026-module inventory contains no Qt and no XfinAudio source modules.

The initial probe caught missing SciPy 1.18 vendored dynamic modules and the wrong
FFmpeg configure raw-PCM muxer name. Focused RED→GREEN tests cover both fixes and
an explicit build-local PyInstaller cache. Corrected FFmpeg SHA256:
1b36118b79dcbe915896212713a0cd2c20278d9cfe50a43cbc9883d97d94d97a.

## Pending and not claimed

- Integration into the final V9 source and its unmodified full release aggregate
- Electron test evidence with all real-runtime integrations and zero skips
- PyInstaller freeze and module inventory audit of that exact verified source
- Relocated empty-PATH package smoke, including original profile engines and M4A
  fallback plus real loudness backup/decoded-PCM/cache checks
- Actual sandboxed graphical Electron launch and desktop playback/native dialogs

The currently authored smoke is test code, not successful runtime evidence.
Legacy macOS/Qt verification does not prove this Linux package. Real user audio,
macOS signing and native installer QA are outside this synthetic Linux scope.

The exact pure-stdlib frozen bootstrap also passed two real dependency-probe cases:
NUMBA_CACHE_DIR absent, and hostile inherited NUMBA_CACHE_DIR/LIBROSA_CACHE_DIR/
NUMBA_CACHE_LOCATOR_CLASSES. The bundle, HOME and global cache were read-only.
Each case completed all six formats, wrote only 52 code-cache files beneath the
trusted --data-dir/cache/numba, and retained disabled librosa Joblib caching.
The warm run reused all code-cache files without changing their size/mtime.
Actual malformed/noncanonical CLI invocations exited before directory creation.
The frozen-aware locator is Numba's standard UserWideCacheLocator with app-owned
XDG_CACHE_HOME; original JIT algorithms and executable-hash invalidation remain
active. No XfinAudio application artifact was built by these probes.

## First application candidate and fixture correction

The first fully gated V9 source passed 4,002 Python tests with 94.48% coverage and
360 Electron tests with no failures/skips. Its Linux application package contains
2,313 frozen modules with no Qt/retired desktop imports. An externally corrected
tagged-fixture smoke passed all six format/profile engines, persistence/cache,
relocation with empty PATH, native boundary services and loudness backup/PCM checks.
The real graphical application launched with Chromium sandbox intact; native
dialog/playback checks continue separately. The original committed smoke command
failed on its untagged WAV fixture, so it is not recorded as a successful run.

The canonical test-only correction has a preceding failing regression, preserves
original scanner behavior and removes the unused untagged-tone generator. It adds
a synthetic-only preparation helper and explicit prerequisites. Final exact-source
gates and rebuilt-artifact smoke are required after this change; their sealed
external reports are authoritative and must accompany delivery.
