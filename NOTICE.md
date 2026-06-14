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
- Other third-party dependencies must be reviewed before binary/app bundle redistribution.

## Trademarks

XfinAudio is an independent project and is not affiliated with, endorsed by, or sponsored by any third-party companies whose products or trademarks are referenced.

- **Mixed In Key** is a trademark of Mixed In Key LLC.
- **Serato**, **Serato DJ Pro**, and related marks are trademarks or registered trademarks of Serato Limited (or Serato Audio Research Ltd.).
- **Camelot**, **Camelot Wheel**, and **Camelot System** are trademarks of Mixed In Key LLC.
- **Open Key Notation** is an open standard and not a proprietary trademark.

All other trademarks, service marks, trade names, logos, and brand identifiers referenced in this project are the property of their respective owners. References to these marks are made solely for descriptive and interoperability purposes under nominative fair use.

## Legal limitation

No legal advice or legal clearance is implied by this notice, the dependency inventory, or any release-readiness documentation. Source publication under GPL-3.0-only does not by itself clear packaged binaries, signed/notarized apps, DMGs, installers, or bundled dependencies for redistribution.
