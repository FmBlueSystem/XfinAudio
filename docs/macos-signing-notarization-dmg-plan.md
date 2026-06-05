# macOS Developer ID signing, notarization, and DMG plan

Status: planning only / not executed

This plan defines the macOS binary/app bundle redistribution path for the GPL-3.0-only full open-source release after the current PyInstaller temp-build validation. No signing, notarization, DMG creation, publishing, or release artifact creation is performed by this plan.

Binary/app bundle redistribution, PySide6/Qt, mutagen, signing/notarization/DMG, and third-party dependencies still require release-specific legal review. No legal clearance is implied.

## Quick path after gates pass

1. Build the PyInstaller `.app` candidate from the approved release process.
2. Sign the generated app with the Developer ID Application certificate.
3. Verify the signature and Gatekeeper execution assessment.
4. Submit the signed app archive or DMG to Apple notarization.
5. Staple the notarization ticket and verify Gatekeeper assessment again.
6. Package the approved app in a DMG and validate mount, copy, and launch behavior.
7. Record all evidence before making any public release or redistribution readiness claim.

## Preconditions and gates

Do not start public signing, notarization, DMG, or binary redistribution work until every gate is satisfied and recorded.

| Gate | Required evidence |
|------|-------------------|
| Clean macOS account validation complete | Completed evidence from `docs/clean-macos-account-validation.md`. |
| PyInstaller unexpected warnings: 0 | Temp build warning triage output showing zero unexpected warnings. |
| Release notes drafted | Candidate notes prepared from `docs/release-notes-template.md`. |
| Manual desktop QA evidence recorded | Human desktop scan/recommend/export evidence with a real Mixed In Key processed folder. |
| Apple Developer Program membership and Team ID available | Team ID recorded outside the repo or in redacted release evidence. |
| Developer ID Application certificate available | Signing identity installed in the release keychain and verified without committing certificate material. |
| notarytool credentials configured securely | Keychain profile or equivalent secret store configured outside the repo. |

## Signing strategy

Sign only the generated `.app` after the temp-build and release gates pass. The intended certificate class is Developer ID Application.

Example command shape, with placeholders only:

```bash
codesign --force --options runtime --timestamp \
  --sign "Developer ID Application: <Company Name> (<TEAMID>)" \
  "dist/XfinAudio.app"
```

Verification commands:

```bash
codesign --verify --deep --strict --verbose=2 "dist/XfinAudio.app"
spctl --assess --type execute --verbose "dist/XfinAudio.app"
```

Record the signing identity hash, exact command, redacted output, app path, macOS version, and result.

## Notarization strategy

Submit either a zipped signed app or the candidate DMG. Prefer the simpler path that preserves app integrity and produces repeatable evidence.

Example command shape, with placeholders only:

```bash
xcrun notarytool submit "XfinAudio.zip" \
  --keychain-profile "<notarytool-profile>" \
  --team-id "<TEAMID>" \
  --wait
```

Staple and verify:

```bash
xcrun stapler staple "dist/XfinAudio.app"
xcrun stapler validate "dist/XfinAudio.app"
spctl --assess --type execute --verbose "dist/XfinAudio.app"
spctl --assess --type open --verbose "XfinAudio.dmg"
```

Record the Notarization UUID, Apple status, staple validation output, and Gatekeeper assessment output.

## DMG strategy

Use candidate tools: `hdiutil` first; `create-dmg` may be evaluated later if layout automation becomes necessary.

Target layout:

- `XfinAudio.app` at the volume root.
- Applications drag target alias.
- Optional README or release notes file with support and safety guidance.
- No scripts that run on mount.

Data safety rules:

- DMG creation must not mutate app-owned data or user library data.
- App-owned paths remain `~/.xfinaudio/xfinaudio.sqlite3` and `~/.xfinaudio/settings.json` at runtime.
- Packaging must not infer write locations from the scanned audio library.

DMG validation must mount, open, copy, and launch the app from a clean macOS account before any distribution claim.

## Secrets handling

Never commit Apple IDs, app-specific passwords, keychain profiles, certificates, private keys, or logs containing credentials.

Additional rules:

- Store notarization credentials in the macOS keychain or another approved secret store.
- Redact Team ID only if the release process treats it as sensitive; always redact Apple IDs and passwords.
- Review logs before attaching them to release evidence.
- Keep certificates and private keys outside the repository and outside release artifacts.

## Evidence template

| Field | Value |
|-------|-------|
| Date/time | |
| Release candidate version | |
| macOS version and architecture | |
| PyInstaller command and output path | |
| PyInstaller unexpected warning count | Expected: `0`. |
| Clean macOS account validation link | |
| Signing identity hash | |
| Signing command | Redact only secrets; preserve command shape. |
| `codesign` verification output | |
| `spctl` execution assessment | |
| Notarization submission command | Redact profile/account details. |
| Notarization UUID | |
| Notarization status output | |
| Staple validation output | |
| DMG creation command | |
| DMG checksum | |
| Gatekeeper open assessment | |
| Clean-account install/launch result | |
| Manual desktop QA evidence link | |
| Final result | Pending / pass / fail. |

## Failure triage

| Failure | First response |
|---------|----------------|
| Signing identity missing | Verify Apple Developer Program access, Team ID, certificate installation, and keychain visibility. Do not generate or commit certificate material in the repo. |
| Hardened runtime or entitlements issue | Capture `codesign` output, inspect required PySide/Qt runtime behavior, and add only minimal entitlements that are justified by evidence. |
| Notarization rejection | Download the notarization log, redact secrets, fix the cited binary or bundle issue, and resubmit only after preserving the original failure evidence. |
| Qt/PySide bundle issue | Inspect bundled frameworks, rpaths, plugins, and PyInstaller collection behavior before changing signing flags. |
| Quarantine or Gatekeeper failure | Capture `spctl` output, quarantine attributes, macOS version, and whether the app was copied from the DMG or launched in place. |

## Explicit non-goals for this step

- Do not run signing commands.
- Do not run notarization commands.
- Do not create a DMG.
- Do not publish or create release artifacts.
- Do not commit certificates, private keys, keychain profiles, Apple IDs, app-specific passwords, or credential-bearing logs.
