# Spec: Manual Mixed In Key QA Evidence

## Goal

Provide a reproducible way to record manual QA evidence for XfinAudio against a real Mixed In Key processed folder.

## Acceptance Criteria

- `scripts/manual_mik_qa_harness.py` exists.
- The script accepts a folder path argument.
- It scans the folder using the real `MetadataScanService`.
- It persists results into a temporary SQLite database.
- It recommends a playlist for each strategy (`build`, `same_energy`, `peak_time`).
- It plans Serato crate exports into a temporary `_Serato_/Subcrates` folder.
- It writes a Markdown evidence file with counts, warnings, and export paths.
- It never writes to the user's real Serato library.
- The script exits nonzero if the folder contains zero complete tracks.
