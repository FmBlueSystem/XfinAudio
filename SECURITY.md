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
- XfinAudio does not mutate audio files outside loudness tag writing.
- The loudness setting is enabled by default and gates both analysis and automatic tag writing; it replaces existing comments. There is no separate tag-write switch.
- XfinAudio does not mutate live Serato database V2 files.
- Other writes are limited to app-owned database, settings, and export files, plus explicit user-requested exports.

Before processing a library, back up any comments you need to retain or disable
“Enable loudness analysis” in Settings. That one setting controls analysis and
write-back together. ID3 writing removes all COMM frames, including custom comments;
FLAC COMMENT and MP4 ©cmt are replaced. Existing unrelated FLAC DESCRIPTION text is
preserved when the loudness line is added/refreshed. Disabling loudness later does
not restore replaced comments. Audio samples are not rewritten by this tag writer.

If you can show a path that violates those boundaries, report it as a security issue.

## Dependency and redistribution caveats

Binary/app bundle redistribution still needs legal review for PySide6/Qt, mutagen, and other third-party dependencies. Dependency metadata in this repository is evidence for review, not a clearance statement.

No legal advice or legal clearance is implied by this security policy.

## AI transport boundary

Configured Nan/OpenAI-compatible endpoints must use HTTPS without URL credentials.
Requests do not follow redirects, including same-origin redirects: configure the
final HTTPS completion URL directly. Bearer keys are not copied to redirected requests.

## Spreadsheet CSV reports

Playlist, metadata-gap, and DJ readiness CSV reports prefix formula-like text cells
with an apostrophe. Detection covers `=`, `+`, `-`, and `@` after leading whitespace,
control, or format characters; numeric columns remain numeric. CSV quoting still
preserves commas, quotes, and line breaks. Depending on the spreadsheet/import mode,
the apostrophe may be visible. Import text columns as text and do not enable formula
evaluation or external content for untrusted metadata. JSON keeps raw metadata
unchanged and is the lossless interchange format. Automated tests check the output;
behavior in a particular spreadsheet application has not been manually certified.
