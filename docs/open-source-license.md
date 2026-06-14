# Open-source license posture

XfinAudio source is distributed as a full open-source project under GPL-3.0-only. This document records the project posture only; it is not legal advice.

## Project license

| Topic | Posture |
|-------|---------|
| Source model | Full open source. |
| Project license | GPL-3.0-only. |
| Project intent | Personal, non-commercial, community-gifted. |
| Source redistribution | Redistribution must comply with GPLv3. |
| Python package (source/wheel) redistribution | Believed to present low legal risk for a non-commercial community project; not a legal clearance. |
| Binary redistribution | Pending legal review for GPLv3 obligations and third-party dependency redistribution obligations (especially PySide6/Qt). |

## Redistribution caveats

- Redistribution must comply with GPLv3 and the licenses for third-party dependencies.
- Source and wheel distribution via PyPI is the intended distribution model.
- Binary and app bundle distribution still needs legal review before publication.
- PySide6/Qt licensing and redistribution obligations remain pending legal review for binary bundles.
- `mutagen` licensing and redistribution obligations remain pending legal review for binary bundles.
- `librosa`, `numpy`, `scipy`, and other scientific-Python transitive dependencies must be reviewed before binary redistribution.
- Other third-party dependencies must be reviewed before binary redistribution.
- No legal advice or legal clearance is implied by this documentation.

## Release implication

Open-source source publication and wheel distribution via PyPI are the current release model. They do not by themselves clear packaged binaries, signed/notarized apps, DMGs, installers, or dependency bundles for redistribution. Release evidence must keep binary redistribution legal review pending until qualified review is completed.
