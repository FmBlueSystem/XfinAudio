# Proposal: Runtime Genre Providers (User-Keyed)

## Intent

Extend the genre enrichment pipeline with the **most popular third-party
providers** as **runtime-only, user-keyed** sources. The user (DJ) supplies
their own API key per provider; no provider data is ever embedded in shipped
assets. The app works perfectly with **no provider enabled** (raw file tags
remain the baseline) and with **any subset** of providers enabled.

This change also ships the **opt-in, default-OFF local LLM tie-breaker**
deferred from the original change. The LLM is a fully separate feature: it
never runs unless the user explicitly enables it, supplies a local model
endpoint, and the judge marked a decision `low_confidence`.

## Motivation

The core enrichment feature (`genre-multi-source-enrichment`) ships with
Discogs (CC0 dumps) and MusicBrainz (CC0) as the two built-in sources. Both
are excellent for the core DJ use case but:

- They don't cover mainstream metadata ecosystems that DJs already have keys
  for (Last.fm scrobbles, Spotify, etc.).
- The most popular sources in the DJ/metadata community — **Last.fm**,
  **Spotify**, **Deezer** — are all under restrictive Terms of Use that
  forbid redistribution of derived datasets, so they cannot be embedded in
  shipped assets. They **can** be used at runtime with a user-supplied key.
- The LLM tie-breaker (deferred from the original change) needs the same
  opt-in, deterministic posture to remain compatible with the project's
  GPL-3.0 + no-online-dependency charter.

## Scope

### In scope

- **Last.fm provider** (runtime-only, user API key). Returns top tags
  (folksonomy) for a track; mapped to canonical genres via the crosswalk
  and denoised via the existing `_TAG_STOPLIST`. Per-user SQLite cache.
- **Spotify provider** (runtime-only, user client credentials). Returns
  artist-level genres (weak signal but mainstream). Per-user SQLite cache.
- **Deezer provider** (runtime-only, no key required for catalog). Returns
  coarse top-level genre buckets for an artist. Per-user SQLite cache.
- **Settings extension**: `api_keys: dict[str, str]` per provider; per-provider
  enable flag; LLM endpoint URL + model name; everything defaults inert.
- **UI**: settings dialog gets a "Genre enrichment" panel with per-provider
  toggles, API key fields (password-style), and the LLM tie-breaker block
  (off by default, local endpoint URL, model name).
- **LLM tie-breaker** (opt-in, default OFF): a local Ollama-compatible
  `/api/generate` client. Invoked only when the judge produces a
  `low_confidence` decision. Restricts the model's choice to the
  already-normalized `top_n` candidates (never invents genres). Uses
  `temperature=0` and caches responses keyed on `(canonical, top_n, model)`
  for determinism and offline-repeatability.
- **License posture** update in `NOTICE.md` documenting the runtime-only,
  user-keyed nature of each new provider, the explicit opt-in for the LLM,
  and the unchanged prohibition on redistributing any provider-derived
  data.

### Out of scope

- Any audio mutation, DSP, fingerprinting, or file writes.
- Automatic sign-up or key management for the user.
- Provider data baked into the repository or the wheel — strict runtime-only.
- Cloud LLM providers (OpenAI, Anthropic, etc.) — local only to preserve
  the project's no-online-dependency posture.
- Live Discogs API integration (Discogs-API ToU is restrictive; CC0 dump
  is already supported and is the recommended path).

## License posture (the hard constraint)

The project is **GPL-3.0-only** and forbids field-of-use restrictions on
redistributed data. All three new providers have Terms of Use that prohibit
redistribution of derived datasets, and Last.fm additionally has a
non-commercial and no-sublicensing clause. The project's own posture
(`NOTICE.md`) declares the project **personal, non-commercial,
community-gifted**.

To remain compatible, the rule is:

> Anything embedded in the distributed app/dataset must be CC0 (or otherwise
> GPL-3.0 compatible). Provider responses under restrictive ToU stay in a
> per-user local cache, never in repo assets.

| Provider | Redistributable? | Use |
|---|---|---|
| Last.fm | **No** (NC, no-sublicense) | Runtime-only with user API key; per-user cache |
| Spotify | **No** (no derived datasets) | Runtime-only with user client credentials; per-user cache |
| Deezer | **No** (no commercial, no derived) | Runtime-only, per-user cache; catalog search needs no key |
| Local LLM (Ollama/llama.cpp) | n/a (user's own model) | Opt-in, default OFF, local endpoint only |

The app's distributable remains 100% CC0. The new providers are pure
runtime extensions; turning them on is a per-user choice and the data
never leaves the user's machine.

## Arbor analysis

Treat the design as a hypothesis tree and refine toward the best route.

### Hypothesis branches

| Branch | Route | Impact | Risk | Cost | License |
|---|---|---|---|---|---|
| P1 | Last.fm only | Medium | Medium (NC + no-sublicense) | Low | OK runtime-only |
| P2 | Spotify only | Low (artist-level only) | Low | Low | OK runtime-only |
| P3 | Deezer only | Low (coarse) | Low | Low | OK runtime-only |
| P4 | All three runtime providers | High | Medium | Medium | OK runtime-only |
| P5 | LLM-as-primary judge | High | High (non-determinism, online) | High | n/a |
| P6 | LLM-as-tie-breaker, local only, opt-in | High | Medium (added complexity) | Medium | n/a |
| P7 | Cloud LLM (OpenAI, Anthropic, etc.) | Medium | High (online, ToS) | Low | depends |
| P8 | Live Discogs API | Low (Discogs-dump covers most) | Medium (ToU) | Medium | OK runtime-only |
| UI1 | Settings dialog (rich) | High | Low | Medium | n/a |
| UI2 | Inline toggles in scan view | Low | Low | Low | n/a |

### Refinement

- Eliminate **P5**: non-determinism and online dependency conflict with
  the project's charter.
- Eliminate **P7**: cloud LLMs introduce an online dependency; the project
  posture is offline-capable.
- Eliminate **P8**: Discogs CC0 dump already provides the main signal;
  live API adds risk for marginal benefit. Defer.
- Adopt **P4 + P6 + UI1**: all three runtime providers + opt-in local LLM
  tie-breaker + a settings dialog for configuration.

### Best route

1. Settings extension with per-provider enable flags and API key fields.
2. Last.fm, Spotify, Deezer as runtime providers (P4).
3. UI for provider + LLM configuration (UI1).
4. Local LLM tie-breaker behind a flag, default OFF (P6).

## Delivery: chained PRs

Estimated total exceeds the 400-line review budget, so this ships as
**chained PRs** on a feature-branch chain. Each slice is independently
reviewable, tested (strict TDD), and behavior-safe (everything defaults
to inert).

| PR | Slice | Approx lines | Depends on |
|---|---|---|---|
| PR1 | Settings extension + license posture docs | ~150 | — |
| PR2 | Last.fm runtime provider | ~350 | PR1 |
| PR3 | Spotify runtime provider | ~300 | PR1 |
| PR4 | Deezer runtime provider | ~250 | PR1 |
| PR5 | UI for providers + LLM configuration | ~300 | PR1–PR4 |
| PR6 | Local LLM tie-breaker (opt-in, default OFF) | ~300 | PR1 |

PR6 is the original PR7 from the previous change; the user explicitly
asked for it to be opt-in and the LLM-not-required scenario to be
preserved. The LLM never runs unless the user enables it.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Provider ToU data leaking into repo | High | Runtime-only; per-user cache; existing `test_genre_license_assets.py` extended with Last.fm/Spotify/Deezer suspect patterns |
| User provides invalid / no API key | Medium | Provider fetch returns `None`; cached error message in settings; app stays functional |
| Provider rate limits | Low | Per-provider throttle + cache, mirroring MB's pattern |
| LLM hallucinating genres outside taxonomy | High | Model's choice is restricted to the already-normalized `top_n`; we post-validate the response against the canonical taxonomy before accepting |
| LLM online dependency | Medium | Local Ollama/llama.cpp only; no cloud fallback; default OFF |
| Non-determinism in LLM | Medium | `temperature=0`, response cached by input hash, same model/seed |
| New dependencies (pylast, spotipy, httpx) | Medium | Pin `>=lower,<upper`; update `uv.lock`; import-guarded for optionality |
| Discogs live API temptation (out of scope) | Low | Explicitly deferred; dump is the canonical path |

## Rollback plan

1. Each provider is independently toggleable. Disable any provider from
   settings and it stops being queried.
2. Removing the providers = revert the PR (or close the feature flag).
3. LLM is opt-in; removing PR6 = the tie-breaker is simply never used.
4. Provider caches are per-user, never in repo, so deletion is non-destructive.

## Success criteria

- [ ] All three providers (Last.fm, Spotify, Deezer) work with user-supplied
      API keys, return canonical candidates, and denoise/restrict as documented.
- [ ] All three providers are off by default and inert when no key is set.
- [ ] Per-provider enable flag in settings; per-provider API key storage.
- [ ] LLM tie-breaker is off by default; local endpoint only; cached; restricted
      to normalized candidates.
- [ ] App is fully functional with **no providers enabled** and **no LLM**.
- [ ] License posture in `NOTICE.md` documents runtime-only/user-keyed nature
      of each new provider and the LLM opt-in.
- [ ] No provider-derived data appears in repo assets (covered by an extended
      license-posture test).
- [ ] All verification commands pass; no audio mutation, no DSP, no Serato V2.
