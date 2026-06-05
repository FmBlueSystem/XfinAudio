# Security Policy

## Supported status

XfinAudio is Pre-release local desktop software. Security handling is best-effort until the project has a public maintainer contact and release process.

## Responsible disclosure

If you find a vulnerability, open a private report through the repository security advisory feature when available. If that is not available yet, open a minimal public issue that asks for maintainer contact without posting exploit details.

Please include:

- affected version, branch, or commit;
- operating system and Python version;
- reproduction steps using synthetic or non-private data;
- expected impact and any safe workaround.

Do not include private audio libraries, private Serato libraries, secrets, Apple credentials, certificates, or personal filesystem paths unless they are sanitized.

## Scope boundaries

Relevant reports include unsafe file writes, export path traversal, dependency vulnerabilities with project impact, secrets exposure, or behavior that violates the documented safety posture.

Not expected by design:

- No live Serato writes by design.
- XfinAudio does not mutate audio files.
- XfinAudio does not mutate live Serato database V2 files.
- The app writes only app-owned database, settings, and export files, plus explicit user-requested exports.

If you can show a path that violates those boundaries, report it as a security issue.

## Dependency and redistribution caveats

Binary/app bundle redistribution still needs legal review for PySide6/Qt, mutagen, and other third-party dependencies. Dependency metadata in this repository is evidence for review, not a clearance statement.

No legal advice or legal clearance is implied by this security policy.
