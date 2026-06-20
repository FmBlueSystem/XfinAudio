# Spec: Smoke shutdown stability

## Requirement: Package smoke mode avoids background spectral work

When `XFINAUDIO_PACKAGE_SMOKE=1` is set, XfinAudio SHALL initialize enough of the desktop app to validate packaging startup and then exit without starting spectral completion workers.

### Scenario: Smoke mode exits cleanly

Given package smoke mode is enabled,
When the desktop app starts,
Then it SHALL NOT start spectral completion workers and SHALL return exit code 0.

## Requirement: Normal runtime behavior remains available

When package smoke mode is disabled, XfinAudio SHALL preserve the existing normal startup path.

### Scenario: Normal app start still shows window

Given package smoke mode is disabled,
When the desktop app starts,
Then it SHALL show and activate the main window as before.
