# Notice

XfinAudio is developed by Freddy Molina at BlueSystem.io (Audio Division).

XfinAudio source is distributed under GPL-3.0-only. See `LICENSE` for the license text.

## Project posture

XfinAudio is a personal, non-commercial, community-gifted open-source project. It is published as source code and as Python source/wheel packages. It is not sold, licensed for profit, or offered as a commercial service. Community redistribution of the source code or wheel must comply with GPL-3.0-only and the licenses of third-party dependencies.

## Distribution intent

The intended distribution is source publication and Python package installation (for example via `pip`, `pipx`, or `uv tool`). In that form the dependency resolver fetches PySide6/Qt, mutagen, and other dependencies directly from PyPI under their own licenses. This model is believed to present low legal risk for a non-commercial community project, but it is not a legal clearance.

Binary, signed, notarized, or bundled app distribution is a separate activity with additional licensing obligations (notably for Qt/PySide6) and remains pending formal legal review before any public redistribution.

## Third-party dependency posture

The project keeps a third-party dependency inventory in `docs/third-party-license-inventory.md`. That inventory is evidence only: it records package metadata available to the project and highlights items that need review.

Known review caveats:

- PySide6/Qt licensing and redistribution obligations require legal review before binary/app bundle redistribution.
- mutagen licensing and redistribution obligations require legal review before binary/app bundle redistribution.
- librosa, numpy, scipy, and other scientific-Python transitive dependencies must be reviewed before binary/app bundle redistribution.
- `musicbrainzngs` is required by the multi-source genre enrichment feature (PR5). The library is MIT-licensed and interacts with the public MusicBrainz service, which is rate-limited to 1 req/s.
- Other third-party dependencies must be reviewed before binary/app bundle redistribution.

## Genre enrichment data sources

The genre enrichment feature (`xfinaudio.genre` package) consumes metadata from third-party services to compute a canonical, consensus-based genre for each track. Source posture:

- **Discogs** — Used via the **CC0 monthly data dumps** only. Discogs styles (the deep electronic taxonomy) are resolved to a canonical Beatport-style vocabulary and stored in a per-user SQLite cache. Live API responses, if ever used, are confined to the per-user cache and never embedded in shipped assets. Discogs data dumps are public domain (CC0-1.0).
- **MusicBrainz** — Used via the **CC0 core genre/tag data** exposed by the public API. The provider is throttled to 1 request per second (per the public service's policy) and cached in a per-user SQLite cache. MusicBrainz supplementary data and the Live Data Feed are not used.
- **Last.fm, Spotify, Deezer** — **Runtime-only, user-keyed.** These providers' Terms of Use prohibit redistribution of derived datasets (Last.fm additionally prohibits non-commercial and sub-licensing use). They are therefore **not** embedded in the repository, the wheel, or the per-user cache as shipped. Each provider is **off by default**; the user (DJ) must explicitly enable it and supply their own API key via settings. API keys live in the user's local app data dir (not the repo). Provider responses are cached locally for the duration of the cache TTL; nothing leaves the user's machine.
- **AcoustID/Chromaprint** — Not used. Audio fingerprinting runs an FFT, which conflicts with the project's no-DSP charter and requires a separate governance decision.
- **Local LLM tie-breaker** — **Opt-in, default OFF.** A local Ollama/llama.cpp endpoint may be configured to break ties on `low_confidence` judge decisions. The local model is restricted to picking among the already-normalized `top_n` candidates (never invents genres). Cloud LLMs are not supported. The tie-breaker is never invoked unless the user explicitly enables it, supplies a local endpoint URL and model name, and the judge produces a `low_confidence` decision. The deterministic judge remains the source of truth.

The shipped in-package data assets are limited to the canonical taxonomy and crosswalk (CC0-1.0).

## Trademarks

XfinAudio is an independent project and is not affiliated with, endorsed by, or sponsored by any third-party companies whose products or trademarks are referenced.

- **Mixed In Key** is a trademark of Mixed In Key LLC.
- **Serato**, **Serato DJ Pro**, and related marks are trademarks or registered trademarks of Serato Limited (or Serato Audio Research Ltd.).
- **Camelot**, **Camelot Wheel**, and **Camelot System** are trademarks of Mixed In Key LLC.
- **Open Key Notation** is an open standard and not a proprietary trademark.

All other trademarks, service marks, trade names, logos, and brand identifiers referenced in this project are the property of their respective owners. References to these marks are made solely for descriptive and interoperability purposes under nominative fair use.

## Legal limitation

No legal advice or legal clearance is implied by this notice, the dependency inventory, or any release-readiness documentation. Source publication under GPL-3.0-only does not by itself clear packaged binaries, signed/notarized apps, DMGs, installers, or bundled dependencies for redistribution.
