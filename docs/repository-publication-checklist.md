# Repository Publication Checklist

Use this checklist when turning the local XfinAudio folder into a public source repository. This is a source publication checklist, not a binary release checklist.

## Source posture

- XfinAudio source is GPL-3.0-only.
- Publish source code, tests, docs, and workflow configuration.
- Do not publish binary artifacts from local `build/`, `dist/`, PyInstaller temp output, app bundles, installers, or DMGs.
- Do not claim signing, notarization, or DMG completion.
- Do not claim legal clearance.
- No private audio files or library databases should be committed or attached to issues.

## Before creating the public repository

- Confirm `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `NOTICE.md`, and `LICENSE` are present.
- Confirm `.github/workflows/non-audio-release-gates.yml` is present for GitHub Actions evidence.
- Confirm `.github/ISSUE_TEMPLATE/bug_report.md`, `.github/ISSUE_TEMPLATE/feature_request.md`, and `.github/pull_request_template.md` are present.
- Confirm `.gitignore` excludes local/runtime artifacts such as `.DS_Store`, `*.bak`, `.venv/`, caches, `build/`, and `dist/`.
- Confirm the tree keeps the safety posture: no audio mutation, no live Serato database V2 mutation, and app-owned writes only.

## Local evidence before push

Run the non-audio gates from the project root:

```bash
uv sync --locked
uv run python scripts/source_package_hygiene_check.py
uv run python scripts/release_gate_check.py --run --report-json /tmp/xfinaudio-release-gate-report.json
uv run python scripts/render_release_gate_evidence.py /tmp/xfinaudio-release-gate-report.json
```

The report should include full tests, lint, format, open-source publication docs, publication artifact hygiene, source package hygiene, PyInstaller check-only metadata, and root artifact hygiene.

## First public push

- Initialize or reuse a Git repository only after confirming the local tree is clean of private data and binary artifacts.
- Add a remote only when the target repository is known; this checklist does not assume a GitHub repository URL.
- Push source and docs first.
- Let GitHub Actions run `.github/workflows/non-audio-release-gates.yml`.
- Review the uploaded JSON/Markdown evidence and GitHub Step Summary before making any release-readiness statement.

## Manual gates that remain pending

The following gates are not proven by source publication or GitHub Actions:

- manual desktop QA with a real Mixed In Key processed folder;
- clean macOS account validation;
- signing, notarization, and DMG creation;
- binary/app bundle redistribution review;
- PySide6/Qt legal review;
- mutagen and other third-party dependency legal review;
- disposable Serato import validation for exported crate fixtures.

## Contributor privacy and safety reminders

- Ask contributors for sanitized logs, paths, screenshots, metadata summaries, and fixture-style examples.
- No private audio files or library databases should be uploaded in public issues or pull requests.
- Reports touching Serato must preserve the no live Serato database V2 mutation boundary.
- Reports touching release packaging must not imply binary readiness unless all manual and legal gates are separately completed and recorded.
