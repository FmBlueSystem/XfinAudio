# Feature: AI via Nan Builders — Fase 0 (nan adapter spike)

## Goal

Establish the first AI integration surface for XfinAudio: a minimal, offline-safe
Nan Builders (OpenAI-compatible) client behind a feature flag. The app must keep
working 100% without network, without a key, and with the flag off.

## Context

- Subscription: Nan Builders, OpenAI-compatible API at `https://api.nan.builders/v1`.
- Validated models via subscription: deepseek-v4-flash, glm5.3-flash, qwen3.6,
  qwen3.8-flash, mimo-v2.5, gemma4.
- Repo has zero network dependencies; use stdlib `urllib.request` (no new deps).
- Precedent pattern (BlueSystemAI STIA spike): synthetic mode by default, live
  only behind an explicit env switch; missing key fails clearly; key never in
  repo/chat/logs.
- This is Fase 0 of the route agreed with the user (Fase 1 copilot, Fase 2
  explainability, Fase 3 batch tagging, Fase 4 embeddings come later).

## Tasks

1. [ ] Branch: create `feat/ai-nan-adapter` from current `main`.
2. [ ] Adapter: `src/xfinaudio/ai/__init__.py` + `src/xfinaudio/ai/nan_client.py`
       — `chat()` via stdlib urllib against `NAN_API_BASE`
       (default https://api.nan.builders/v1/chat/completions), `NAN_API_KEY`
       from env, configurable `NAN_MODEL` (default `deepseek-v4-flash`),
       request timeout, single bounded behavior, key never logged.
3. [ ] Feature flag + key resolution: `is_ai_enabled()` reading `XFINAUDIO_AI_ENABLED`
       (default off). API key resolution order: env `NAN_API_KEY` -> env file.
       Env-file loader (`load_api_key_from_env_file`) supports both a bare key
       line and dotenv-style `NAN_API_KEY=...`; path resolution: explicit param
       -> `XFINAUDIO_AI_ENV_FILE` -> `~/.xfinaudio/apiIA.env`. Key value NEVER
       appears in errors, reprs, or logs.
       User parameter decision (2026-09-28): the real key lives in
       `/Users/freddymolina/Desktop/XfinAudio/apiIA.env` (bare-key format,
       chmod 600 applied, gitignored in repo). A follow-up task adds an
       `AiSettings` section to config/settings.py storing ONLY `enabled` and
       `env_file` path — never the key itself.
4. [ ] Tests: `tests/test_nan_client.py` — synthetic/no-network tests with a
       fake transport; contracts: default-off flag, missing-key error text
       names the env var, timeout honored, key absent from raised errors,
       request payload shape (model, messages), response parsing.
5. [x] Verification: `uv run pytest -q`, `uv run ruff check .`,
       `uv run ruff format --check .`, `uv run pyright src tests`.
6. [x] Work-unit commit (Conventional Commit) staging only the new paths.

All tasks complete: commit 2e3bffd on feat/ai-nan-adapter (2026-09-28).
Follow-up (separate task): add `AiSettings` (enabled + env_file path, never the
key) to config/settings.py + settings persistence tests.

## Constraints

- No new third-party dependencies.
- Live calls are NOT part of this spike (entitlement/NAN_API_KEY unverified);
  tests must be fully offline.
- Do not touch the dirty in-flight files (library_screen*).

## Evidence

- Commit: `2e3bffd feat(ai): add offline-by-default Nan Builders adapter spike`
- Suite: 58 adapter tests + full suite 2096 passed; ruff check/format clean;
  pyright 0 errors (verified independently by orchestrator post-writer).
- Deliberate deviation (tested): `chat()` raises NanConfigError when the flag is
  OFF, making the flag authoritative against accidental network reach.
- Credential safeguard: /Users/freddymolina/Desktop/XfinAudio/apiIA.env is
  bare-key format, chmod 600, gitignored; its value was never read into any
  session log.
