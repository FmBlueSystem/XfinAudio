# Verification

- Required original SoundFile and Setuptools notices: 20 files from pinned installed distributions, including external codec notes and all selected vendor/configuration notices; exact bytes and target paths covered.
- Missing, empty, wrong-version or outside-input notices: fail closed in focused regressions.
- Project and Electron notices: mandatory before assembly output creation; Mac now includes the project NOTICE.
- Copied notices: hash checks at assembly and after final signing/archive preparation wiring. A dedicated mocked-main regression for the final verification calls is not included; the helpers, command and assembly paths are tested.
- Strict RED: 103 failed and 42 passed. Focused GREEN: 145 passed. Ruff, formatting and targeted Pyright passed. Independent review found no blocking issue.
- Actual locked Linux build input probe: 20 files, 90,136 bytes, all original RECORD/hash checks passed.

Complete combined-source local and hosted gates are pending and will be recorded outside the final immutable source seal. No fresh binary or native acceptance is claimed. Notice-file mechanics do not establish license/corresponding-source completeness, and no prior executable is relabeled as 2.2.0. The separately received Mac component dossier contains concrete unresolved source/build inputs; those remain binary release prerequisites.
