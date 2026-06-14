# Release Notes Template

Copy this template for each XfinAudio release candidate or release. Keep claims tied to recorded verification evidence.

```markdown
# XfinAudio <version> Release Notes

Date: <YYYY-MM-DD>

## Summary

<One short paragraph describing the release outcome and why it matters.>

## Who should use it

- <Intended tester/user group.>
- <Required environment or platform.>

## What is included

- <Feature, fix, or validation item.>
- <Feature, fix, or validation item.>
- <Documentation or release-readiness item.>

## License posture

- XfinAudio source is full open source under GPL-3.0-only.
- Redistribution must comply with GPLv3 and third-party dependency obligations.
- PySide6/Qt, mutagen, and dependency obligations remain pending legal review before binary/app bundle redistribution.
- No legal clearance is implied by these notes.

## Explicitly out of scope

- No audio file mutation.
- No live Serato writes.
- No installer, signing, notarization, or publishing claim unless separately verified.
- <Any release-specific non-goal.>

## Verification evidence

- Automated tests: `<command>` — <result/link>.
- Ruff lint: `<command>` — <result/link>.
- Ruff format check: `<command>` — <result/link>.
- Release smoke: `<command>` — <result/link>.
- Manual desktop QA: <tester/date/evidence link or "pending">.

## Known limitations

- Serato fixture validation is not live Serato compatibility.
- Live Serato library writes are not verified as part of this release candidate; any Serato crate export must be treated as experimental and requires a manual backup and verification step.
- Manual desktop QA with a real Mixed In Key processed folder is required before release claims.
- Binary redistribution legal review remains pending for PySide6/Qt, mutagen, and third-party dependencies.
- <Release-specific limitation.>

## Safe-use warnings

- XfinAudio must not mutate source audio files.
- Do not write to a live Serato library from this release candidate.
- Use safe export folders outside the scanned audio library.
- Treat fixture-based Serato checks as dry-run validation only.

## Upgrade and data notes

- App database path: `~/.xfinaudio/xfinaudio.sqlite3`.
- Settings path: `~/.xfinaudio/settings.json`.
- <Any migration, backup, or reset notes.>

## Support and troubleshooting

- Re-run the release smoke script before reporting release-readiness failures.
- Include platform, command output, and relevant evidence links in reports.
- <Project support contact or issue tracker.>
```
