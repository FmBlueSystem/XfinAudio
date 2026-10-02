# Requirements

## R1 — Consent and configuration
GIVEN default settings WHEN Settings opens THEN AI is disabled and no request is made.
GIVEN an explicit operator environment override WHEN Settings opens THEN the effective enabled/file values are shown.
GIVEN a successful save WHEN AI is enabled or disabled THEN subsequent requests use the new value immediately.
GIVEN a cancelled dialog or failed save WHEN settings were edited THEN persisted and runtime configuration stay unchanged.

## R2 — Credential boundary
GIVEN settings are opened or saved THEN no key value is displayed, stored in settings, or read from a credential file by the UI.
GIVEN a user chooses an existing credential file THEN only its path is stored.
GIVEN configuration guidance THEN it describes operator-owned secure configuration outside the app.

## R3 — Data disclosure and connection test
GIVEN AI controls THEN they identify Nan Builders and explain request/metadata sharing, never audio or local paths.
GIVEN Test connection is clicked with AI enabled THEN only a disclosed synthetic prompt, model and app identifier are sent with authentication, never library content.
GIVEN a disabled or missing configuration THEN no transport is called and recovery guidance is visible.
GIVEN invalid configuration, authentication, unavailable network or malformed response THEN status is bounded and contains no key, raw response or transport detail.

## R4 — Responsive and reversible UI
GIVEN an in-flight probe THEN the UI remains responsive and duplicate tests are blocked.
GIVEN Cancel test, closing, changing configuration or saving THEN old results cannot overwrite the current UI.
GIVEN a finished or cancelled probe THEN retry is possible without restarting the app; cancellation does not claim to recall an already sent request.
