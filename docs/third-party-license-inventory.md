# Third-party dependency/license inventory

This document combines a manually reviewed Electron/Qt-free migration supplement with a preserved legacy direct-Python metadata snapshot and FFmpeg provenance.
It is evidence for release readiness review, not legal clearance.

## Electron/Qt-free migration scope (2026-10-01)

This manually maintained supplement records dependency declarations and observed metadata, not a complete binary bill of materials or a license-compatibility determination. It covers the new `desktop-electron/` and headless Python path. The root `pyproject.toml`, `uv.lock`, and original UI remain legacy Qt-bearing inputs; installing the root project is not a Qt-free installation.

Evidence: committed npm/headless/freezer locks, matching installed Linux Python distribution metadata and license files, the installed Electron distribution, and notice-presence checks in the earlier V9 Linux package. All 32 headless package versions below matched installed metadata at review time. The exact native Mac closure was not present for this review. Linux evidence does not establish Mac contents or approval to redistribute either platform. Dependency locks record selected packages/artifact integrity; they do not themselves contain the runtimes or prove license compliance.

### Hash-locked headless Python dependencies

`desktop-electron/requirements-headless.in` declares Mutagen, Pydantic, NumPy and librosa; `requirements-headless.txt` pins the full 32-package closure with SHA-256 artifact hashes. License cells prefer installed `License-Expression`, then `License`, then license classifiers. Labels are metadata as supplied, not newly inferred SPDX classifications. SciPy's long license field is described rather than truncated into a misleading single identifier.

| Package | Locked version | Observed license metadata |
|---------|----------------|---------------------------|
| `annotated-types` | 0.8.0 | MIT |
| `audioread` | 3.1.0 | MIT |
| `certifi` | 2026.7.22 | MPL-2.0 |
| `cffi` | 2.1.1 | MIT-0 |
| `charset-normalizer` | 3.5.2 | MIT |
| `cloudpickle` | 3.1.2 | BSD-3-Clause |
| `decorator` | 5.3.1 | BSD-2-Clause |
| `idna` | 3.20 | BSD-3-Clause |
| `joblib` | 1.6.0 | BSD-3-Clause |
| `lazy-loader` | 0.6 | BSD-3-Clause |
| `librosa` | 0.11.0 | ISC |
| `llvmlite` | 0.50.0 | BSD-2-Clause AND Apache-2.0 WITH LLVM-exception |
| `msgpack` | 1.2.3 | Apache-2.0 |
| `mutagen` | 1.48.1 | GPL-2.0-or-later |
| `narwhals` | 2.26.0 | MIT |
| `numba` | 0.68.0 | BSD |
| `numpy` | 2.5.3 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| `packaging` | 26.3 | Apache-2.0 OR BSD-2-Clause |
| `platformdirs` | 4.12.2 | MIT |
| `pooch` | 1.9.0 | BSD-3-Clause |
| `pycparser` | 3.0 | BSD-3-Clause |
| `pydantic` | 2.13.5 | MIT |
| `pydantic-core` | 2.46.5 | MIT |
| `requests` | 2.34.2 | Apache-2.0 |
| `scikit-learn` | 1.9.1 | BSD-3-Clause |
| `scipy` | 1.18.1 | Full license/third-party text in `License`; classifier: BSD License; see `scipy-1.18.1.dist-info/LICENSE.txt` |
| `soundfile` | 0.14.0 | BSD 3-Clause License |
| `soxr` | 1.1.0 | LGPL-2.1-or-later |
| `threadpoolctl` | 3.7.0 | BSD-3-Clause |
| `typing-extensions` | 4.16.0 | PSF-2.0 |
| `typing-inspection` | 0.4.4 | MIT |
| `urllib3` | 2.8.0 | MIT |

### npm lock metadata

`desktop-electron/package.json` directly pins Electron 44.5.1, TypeScript 7.0.2 and `@types/node` 26.6.3. The v3 `package-lock.json` records the following 36 non-root entries, all with registry URLs and SHA-512 integrity values and all marked development dependencies. The optional TypeScript platform packages are alternative compiler binaries, not evidence that every platform is installed or bundled. These `license` fields do not replace each component's actual notices.

| Lock package path | Locked version | License field |
|-------------------|----------------|---------------|
| `node_modules/@electron-internal/extract-zip` | 1.0.5 | BSD-2-Clause |
| `node_modules/@electron/get` | 5.1.0 | MIT |
| `node_modules/@types/node` | 26.6.3 | MIT |
| `node_modules/@typescript/typescript-aix-ppc64` | 7.0.2 | Apache-2.0 |
| `node_modules/@typescript/typescript-darwin-arm64` | 7.0.2 | Apache-2.0 |
| `node_modules/@typescript/typescript-darwin-x64` | 7.0.2 | Apache-2.0 |
| `node_modules/@typescript/typescript-freebsd-arm64` | 7.0.2 | Apache-2.0 |
| `node_modules/@typescript/typescript-freebsd-x64` | 7.0.2 | Apache-2.0 |
| `node_modules/@typescript/typescript-linux-arm` | 7.0.2 | Apache-2.0 |
| `node_modules/@typescript/typescript-linux-arm64` | 7.0.2 | Apache-2.0 |
| `node_modules/@typescript/typescript-linux-loong64` | 7.0.2 | Apache-2.0 |
| `node_modules/@typescript/typescript-linux-mips64el` | 7.0.2 | Apache-2.0 |
| `node_modules/@typescript/typescript-linux-ppc64` | 7.0.2 | Apache-2.0 |
| `node_modules/@typescript/typescript-linux-riscv64` | 7.0.2 | Apache-2.0 |
| `node_modules/@typescript/typescript-linux-s390x` | 7.0.2 | Apache-2.0 |
| `node_modules/@typescript/typescript-linux-x64` | 7.0.2 | Apache-2.0 |
| `node_modules/@typescript/typescript-netbsd-arm64` | 7.0.2 | Apache-2.0 |
| `node_modules/@typescript/typescript-netbsd-x64` | 7.0.2 | Apache-2.0 |
| `node_modules/@typescript/typescript-openbsd-arm64` | 7.0.2 | Apache-2.0 |
| `node_modules/@typescript/typescript-openbsd-x64` | 7.0.2 | Apache-2.0 |
| `node_modules/@typescript/typescript-sunos-x64` | 7.0.2 | Apache-2.0 |
| `node_modules/@typescript/typescript-win32-arm64` | 7.0.2 | Apache-2.0 |
| `node_modules/@typescript/typescript-win32-x64` | 7.0.2 | Apache-2.0 |
| `node_modules/debug` | 4.4.3 | MIT |
| `node_modules/electron` | 44.5.1 | MIT |
| `node_modules/electron/node_modules/@types/node` | 24.19.0 | MIT |
| `node_modules/electron/node_modules/undici-types` | 7.24.6 | MIT |
| `node_modules/env-paths` | 3.0.0 | MIT |
| `node_modules/graceful-fs` | 4.2.11 | ISC |
| `node_modules/ms` | 2.1.3 | MIT |
| `node_modules/progress` | 2.0.3 | MIT |
| `node_modules/semver` | 7.8.5 | ISC |
| `node_modules/sumchecker` | 3.0.1 | Apache-2.0 |
| `node_modules/typescript` | 7.0.2 | Apache-2.0 |
| `node_modules/undici` | 7.30.0 | MIT |
| `node_modules/undici-types` | 8.9.0 | MIT |

### Runtime and freezer evidence beyond the two application locks

- The inspected Linux Electron 44.5.1 executable reports embedded Node.js 24.21.0 and Chromium 152.0.7977.130 via `process.versions`. Electron's npm package is MIT; Chromium, Node.js, V8 and their dependencies have their own notices. Retain the exact Electron distribution's `LICENSE` and `LICENSES.chromium.html` and verify component-notice coverage for the delivered platform. The [Electron license](https://github.com/electron/electron/blob/main/LICENSE) and [Node.js license collection](https://github.com/nodejs/node/blob/main/LICENSE) are upstream review references, not substitutes for matching release material
- The review host's build tools report Node.js 24.19.0 and npm 11.9.0. These are observations, not pins in `package-lock.json`, and `@types/node` versions are type declarations, not Node runtime versions. TypeScript and npm are build tooling; determine whether any of their files are actually shipped before assigning binary inventory scope
- The inspected Python interpreter is CPython 3.12.14; the headless lock targets Python 3.12 but does not lock an interpreter distribution. The Linux freezer recipe copies that interpreter's `LICENSE.txt` to `_internal/licenses/python/LICENSE.txt`. Preserve its PSF/history/third-party notices and inspect the selected runtime's native dependencies separately
- `packaging/linux/requirements-build.txt` pins the 32 headless packages plus `altgraph` 0.17.5 (installed metadata: MIT), `pyinstaller` 6.20.0 (metadata: GPLv2-or-later with its special exception), `pyinstaller-hooks-contrib` 2026.5 and `setuptools` 82.0.1 (MIT). `packaging` 26.3 is already in the headless closure. The inspected hooks-contrib `licenses/LICENSE` assigns GPL-2.0-or-later to standard hooks/files and Apache-2.0 to runtime hooks; preserve the actual terms and identify which files enter a bundle
- `packaging/macos/requirements-build.txt` includes the Linux build lock and adds hash-pinned `macholib` 1.16.4, for 37 effective packages. Its exact installed metadata/licenses and the native Mac build environment were not inspected here; those remain to be captured on the selected Mac. A lock entry is not evidence of its installed or redistributed contents

### Native-wheel notice evidence and remaining review

The 32-row Python table is not a native-library closure. In the inspected Linux wheels:

- NumPy and SciPy ship OpenBLAS/LAPACK, libgfortran and libquadmath libraries. Their wheel `LICENSE.txt` files identify those components and additional terms, including the GCC Runtime Library Exception. NumPy's metadata expression alone does not enumerate all these binary-library terms; retain the complete wheel notices and match the actual native inventory
- llvmlite provides `licenses/LICENSE.thirdparty` for LLVM; Numba provides `licenses/LICENSES.third-party`; SoXR provides `COPYING.LGPL`, `LICENSE-libsoxr.txt` and `LICENSE-PFFFT.txt` alongside its own `LICENSE.txt`. Check source/build and redistribution requirements against the files actually included
- SoundFile ships `_soundfile_data/libsndfile_x86_64.so` and `_soundfile_data/COPYING`, separate from its own BSD license. Its installed `licensing/license_notes.md` identifies libFLAC, LAME, mpg123, Ogg, Opus and Vorbis copyright/source notices. That notes file was absent from the inspected V9 Linux package even though libsndfile's `COPYING` was present. This is an outstanding notice-coverage item, not a finding about an uninspected new or Mac binary

The Linux recipe copies Python distribution metadata and retains the FFmpeg 7.1.1 source archive, checksum, license and configure inputs. Those checks do not establish that every embedded library's notices/source are present. The Mac recipe verifies selected FFmpeg closure hashes, but a nonempty dependency-license directory does not prove coverage; copying caller-supplied notices/provenance is not a corresponding-source audit. It also copies Electron notice files only if present, so successful assembly does not prove they were supplied. Inspect each final bundle and its source package before a separate binary-release decision.

### Binary redistribution remains a separate review gate

1. Inventory the exact shipped Electron/Chromium/Node, CPython, frozen modules, native wheel libraries and FFmpeg dependency closure per platform. Match names, versions, build configuration, hashes, notices and source/build provenance to those bytes. This source inventory does not approve a runtime, app, DMG or other binary distribution
2. Retain and deliver component copyright/license/NOTICE material, including notices outside Python `dist-info`, and the matching corresponding source/build instructions wherever required by the applicable terms. Review the actual distribution method and any proposed written source offer; a download URL and checksum alone are not a reviewed offer. The [FFmpeg compliance guidance](https://ffmpeg.org/legal.html) describes exact-source and build-instruction expectations
3. Verify each FFmpeg binary's actual `-version`, `-buildconf` and `-L` output against retained source/configuration. Capability, hash and host-library checks alone do not establish the selected license configuration. Optional GPL/nonfree features change the licensing/distribution analysis described by [FFmpeg's license documentation](https://ffmpeg.org/doxygen/trunk/md_LICENSE.html). The historical universal2 recipe below is not evidence for a caller-supplied Mac FFmpeg/dylib closure
4. Keep the existing `NOTICE.md` binary-review gate. Qt-free module/native checks establish the absence of Qt in a particular checked bundle, not satisfaction of Electron, Python, Mutagen, scientific-library, FFmpeg or codec obligations. Test success, ad-hoc signing and non-commercial intent are not binary-redistribution clearance

## Legacy direct-Python snapshot

The following historical table was generated from the root project declarations and then-installed Python metadata. It is preserved for legacy provenance, not as the current headless dependency list. “Not provided” reflects that generator's legacy metadata reader, which does not read `License-Expression`.

| Name | Version | License metadata | Summary | Homepage / project URL | Legal review note |
|------|---------|------------------|---------|------------------------|-------------------|
| hatchling | Not provided in package metadata | Not provided in package metadata | Not provided in package metadata | Not provided in package metadata | Package was declared by the project but not found in installed distribution metadata. |
| mutagen | 1.47.0 | GPL-2.0-or-later | read and write audio tags for many formats | https://github.com/quodlibet/mutagen | — |
| pydantic | 2.13.4 | Not provided in package metadata | Data validation using Python type hints | https://github.com/pydantic/pydantic | — |
| pyinstaller | 6.20.0 | GPLv2-or-later with a special exception which allows to use PyInstaller to build and distribute non-free programs (including commercial ones) | PyInstaller bundles a Python application and all its dependencies into a single package. | https://pyinstaller.org | — |
| pyobjc-framework-Cocoa | 12.2 | MIT | Wrappers for the Cocoa frameworks on macOS | https://github.com/ronaldoussoren/pyobjc | — |
| pyright | 1.1.410 | MIT | Command line wrapper for pyright | https://github.com/RobertCraigie/pyright-python | — |
| PySide6 | 6.11.1 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | Python bindings for the Qt cross-platform application and UI framework | https://pyside.org | PySide6/Qt licensing requires legal review before binary redistribution. |
| pytest | 9.0.3 | Not provided in package metadata | pytest: simple powerful testing with Python | https://docs.pytest.org/en/latest/ | — |
| pytest-cov | 7.1.0 | License :: OSI Approved :: MIT License | Pytest plugin for measuring coverage. | Not provided in package metadata | — |
| ruff | 0.15.15 | Not provided in package metadata | An extremely fast Python linter and code formatter, written in Rust. | https://docs.astral.sh/ruff | — |
| setproctitle | 1.3.7 | BSD-3-Clause | A Python module to customize the process title | https://github.com/dvarrazzo/py-setproctitle | — |

## Legacy bundled FFmpeg CLI provenance

This retained entry describes the original macOS universal2 source-build recipe. It does not inventory the newer caller-selected native Mac closure or replace the Linux recipe's retained inputs.

| Field | Value |
|-------|-------|
| Component | FFmpeg 7.1.1 CLI |
| Official source | https://ffmpeg.org/releases/ffmpeg-7.1.1.tar.xz |
| SHA-256 | `733984395e0dbbe5c046abda2dc49a5544e7e0e1e2366bba849222ae9e3a03b1` |
| License status | LGPL-2.1-or-later configuration; `--disable-gpl` and `--disable-nonfree` are required. |
| Build/source availability | Rebuild from source with `uv run python scripts/build_ffmpeg_universal.py --work-directory /tmp/xfinaudio-ffmpeg --output packaging/ffmpeg/ffmpeg`; retain the official source URL and checksum with every bundle. |
| Target | macOS universal2 (`arm64`, `x86_64`), macOS 11.0 minimum. |
| Bundled location | Bundle root `ffmpeg`, resolved by the frozen runtime as `_MEIPASS/ffmpeg`. |

The source builder downloads only this archive and checks its pinned SHA-256 before
extraction or compiler execution. It does not download or verify a detached PGP
signature. This is checksum-based integrity, not an independently verified signer identity.

### Exact build surface

Disabled: `--disable-everything`, `--disable-gpl`, `--disable-nonfree`, `--disable-network`, `--disable-doc`,
`--disable-debug`, `--disable-autodetect`, and `--disable-ffprobe`.

Enabled: `--enable-ffmpeg`, `--enable-avcodec`, `--enable-avformat`, `--enable-avfilter`, `--enable-avutil`,
`--enable-protocol=file`; demuxers `--enable-demuxer=aiff`, `--enable-demuxer=flac`, `--enable-demuxer=mp3`,
`--enable-demuxer=wav`, `--enable-demuxer=mov`; decoders `--enable-decoder=flac`, `--enable-decoder=mp3`, `--enable-decoder=aac`, `--enable-decoder=alac`, `--enable-decoder=pcm_s16be`,
`--enable-decoder=pcm_s16le`, `--enable-decoder=pcm_s24be`, `--enable-decoder=pcm_s24le`,
`--enable-decoder=pcm_s32be`, `--enable-decoder=pcm_s32le`; filters `--enable-filter=ebur128`,
`--enable-filter=aformat`, `--enable-filter=aresample`; `--enable-muxer=null`; and encoders
`--enable-encoder=pcm_s16le`, `--enable-encoder=wrapped_avframe`.

Corresponding-source retention/review: retain the exact source archive, checksum, build script, and configuration
for every bundled binary. Review corresponding-source delivery and any proposed durable written offer against the applicable
license and distribution method. The source URL and checksum above are provenance, not an approved offer template.

The generated executable is intentionally not committed. Packaging fails closed unless this exact source-built,
executable, universal2 FFmpeg 7.1.1 binary supports `ebur128=peak=true` and MOV/AAC/ALAC M4A decoding. This provenance entry does not clear
legal review or binary redistribution obligations.

## Limitations and legal review gates

- XfinAudio source is GPL-3.0-only, but dependency metadata does not clear redistribution obligations.
- Package metadata may be incomplete, ambiguous, or different from the license terms that apply to redistribution.
- PySide6/Qt licensing requires legal review before binary redistribution.
- mutagen and other third-party dependencies require legal review before binary redistribution.
- No legal clearance or binary redistribution approval is implied by this inventory.

## Reproduce

The existing script still reads only direct root `pyproject.toml` dependencies and installed metadata; it does not generate the migration supplement, resolve the headless transitive closure, read npm locks, or audit binaries. Its historical output/schema are unchanged. Do not overwrite this curated document with that output.

```bash
uv run python scripts/third_party_license_inventory.py
uv run python scripts/third_party_license_inventory.py --format json --output /tmp/xfinaudio-third-party-inventory.json
```

To refresh the migration tables, compare every non-root `packages` entry in `desktop-electron/package-lock.json` (`version`, `license`, `resolved`, `integrity`) and every pinned requirement in `desktop-electron/requirements-headless.txt`. In a matching installed environment, inspect `importlib.metadata.distribution(name).metadata`, preferring `License-Expression`, then `License`, then license classifiers, and retain the full `License-File`/`RECORD` evidence. Reinspect platform-native notices rather than copying Linux results to Mac. Run the lock-coverage regression:

```bash
python -m pytest --noconftest -q tests/test_migration_license_inventory_docs.py
```
