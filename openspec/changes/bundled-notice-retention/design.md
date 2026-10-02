# Design

Extend the shared Linux freezer recipe used by Mac with a bounded notice collector based on the selected locked distributions' metadata/RECORD. Copy notice resources outside dist-info without changing executable modules or dependency locks. Retain stable relative provenance and original bytes; do not copy arbitrary package trees as an undocumented workaround.

Require project/Electron notice inputs before platform assembly writes a new destination. Preserve Linux full-distribution copying and Mac executable rename/plist/ad-hoc integrity-signing behavior. Do not change the FFmpeg dependency-license manifest interface in this slice; its actual component/source dossier remains parent-coordinated and outstanding.
