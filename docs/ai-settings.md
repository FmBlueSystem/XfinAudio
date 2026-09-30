# Optional AI settings

AI is off by default. The deterministic playlist tools remain available without a provider, key or network connection.

Open **Settings → AI Settings**, or use a **Configure AI** action. Nan Builders is the supported provider. The recipient host is shown, including a custom HTTPS endpoint supplied by the operator. Opening Settings, choosing a file, toggling the checkbox and cancelling never send a request.

## Credentials stay outside Settings

The app does not provide a key text field and does not write credential files. Configure `NAN_API_KEY` in the launch environment or in an operator-owned env file outside the app. Keep that file private with owner-only access; do not place it in a repository, shared folder, screenshot or support log.

An existing env file may contain a bare key or a `NAN_API_KEY` assignment. The default path is `~/.xfinaudio/apiIA.env`. **Choose existing env file** selects only its path; **Use default file** clears the custom path. The UI inspects presence, not the file contents. The adapter reads the credential only when an explicitly requested AI operation runs.

Environment credentials take precedence over file credentials. Existing launcher controls remain supported:
- `XFINAUDIO_AI_ENABLED` controls the initial enable override
- `XFINAUDIO_AI_ENV_FILE` controls the initial file override
- `NAN_API_BASE` selects an absolute HTTPS endpoint; credential-bearing redirects are rejected
- `NAN_MODEL` selects the provider model

Settings displays effective initial enable/file overrides. Pressing **OK** explicitly saves the selected preference and changes subsequent runtime requests immediately. A later relaunch still respects explicit launch overrides. Failed saves preserve prior preferences. No restart is required for AI changes; changing UI language retains its existing restart requirement.

## What is sent

Requested AI actions may send request text and track/set metadata such as titles, artists, genres, BPM, key, energy and transition/readiness summaries. They do not send audio files or local file paths. The UI shows this disclosure before opt-in.

**Test connection** sends only `Reply with OK. XfinAudio connection test.`, plus the selected model name and app identifier, authenticated with the configured credential. No library content is sent. This may consume provider quota. Testing uses the staged configuration and does not save it or enable other AI actions.

A configuration-present status is not a connection success. Missing or invalid credentials, rejected authentication, malformed responses and network failures display recovery guidance, while offline tools continue working. The UI never displays provider response text or raw transport errors.

The test runs in the background. Duplicate clicks are blocked. **Cancel test**, closing Settings or editing the configuration discards pending results. An already sent request cannot be recalled; retry becomes available when that bounded request finishes.

## Verification boundary

Development and automated tests use synthetic credentials, fake responses and injected transports only. They validate the interaction and security boundaries; they do not verify a real subscription, key or provider connection.
