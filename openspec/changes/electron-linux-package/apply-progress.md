# Apply progress

2026-10-01: Work is isolated in a packaging staging checkout; the active V8/V9
the aggregate source tree remained unchanged during dependency preparation.

- Strict RED captured for missing assembly/gate/audit contract (18 failures),
  licenses (1), raw PCM verification profile (1), relative-only relocation (1),
  FFmpeg capability/dependency validation (2), frozen librosa assets/PATH (2),
  Electron no-skip evidence (1), and exact freezer lock (1)
- GREEN: 38 focused packaging tests pass; ruff lint/format pass; explicit Pyright
  for packaging plus tests reports zero errors/warnings in the verification env
- Frozen entry uses only _MEIPASS on PATH; existing app/native confirmations and
  original analyzers are unchanged
- V9's expanded hash-locked runtime (librosa/numba/scipy/soundfile chain) is included
  in a separate clean freezer environment; all installed versions exactly match
  its lock and PySide6 is absent
- FFmpeg 7.1.1 official source compiled with recorded minimal static-library flags;
  executable SHA256: 1b36118b79dcbe915896212713a0cd2c20278d9cfe50a43cbc9883d97d94d97a
- Actual 65-second synthetic WAV, FLAC, MP3, AAC-M4A, ALAC-M4A and AIFF passed
  true-peak ebur128 analysis with an empty PATH. ldd reports only libc/libm/loader
- Relocated package smoke is authored and syntax-checked, including real original
  profile completion/persistence/cache and confirmed loudness tag/backup/PCM/cache
- No application package has been built; final V9 merge and exact-tree aggregate
  remain prerequisites. Sandboxed GUI launch is a separate verification step

Dependency-only preflight found and corrected two defects before application
packaging: SciPy 1.18 vendored NumPy FFT/linalg requires explicit hidden imports,
and FFmpeg's configure muxer name is pcm_s16le (its CLI format name is s16le).
Captured RED covers the dynamic modules/cache environment and actual muxer/encoder
preflight; all 38 tests pass after the narrow fixes. A dedicated PyInstaller cache
avoids writing to the build host's read-only home. No original algorithm or JIT
behavior is disabled; the dependency-only probe uses real feature computations.

The corrected dependency-only executable now passes cold and warm runs across
all six formats from a relocated read-only folder with an initially empty PATH.
The inventory contains 2,026 dependency modules and no Qt or XfinAudio modules.
All source byte hashes/mtimes are preserved; 52 JIT cache files are confined to
isolated test data and reused without changes on the warm run. The application
artifact and graphical launch remain unbuilt/unverified at this checkpoint.

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

Final application freeze and sandboxed Linux GUI launch succeeded on the first
exact-source-gated candidate. The first full application smoke exposed a test-only
fixture error: its generated WAV had no metadata tags, so the unchanged original
scanner correctly skipped it. An externally corrected harness completed all real
engines, persistence, empty-PATH relocation and loudness safety assertions.

The canonical harness now copies the tagged WAV from its required synthetic
profile fixture directory. A regression first failed against the old harness and
proves both original scan cases (untagged skipped, tagged read without mutation).
A fixture-preparation helper and explicit tagged-input instructions make the run
reproducible. Application/runtime source is unchanged. Exact-source aggregate and
package evidence must be resealed for this test/documentation-only correction.
