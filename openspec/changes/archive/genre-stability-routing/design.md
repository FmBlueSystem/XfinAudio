# Design: Genre-Stable Playlist Routing

## Decision question

How do we guarantee genre coherence in a recommendation without breaking the flexibility of the other 7 strategies?

## Alternatives considered (Arbor-style)

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. New "Same Genre" strategy with pre-scorer filter | Opt-in; mirrors `same_color`; isolated risk; easy to test. | Adds one more entry in the combo. | **Selected.** |
| B. Add genre penalty to all strategies | Universal improvement. | Hidden behavior change; can suppress valid harmonic matches. | Rejected for now. |
| C. Make genre a hard constraint in the optimizer | Algorithmic correctness. | Touches the optimizer; bigger refactor; harder to rollback. | Rejected. |
| D. Require a "genre focus" input from the DJ | Explicit. | More UI clutter; duplicates the same pattern as Prep Copilot. | Rejected. |

## Architecture impact

```text
BuildScreen (combo)
    │ recommend_requested("same_genre", ...)
    ▼
PlaylistRecommendationService.recommend(strategy="same_genre")
    │ reads anchor genres
    │ filters records to matching primary genre
    ▼
recommend_playlist(records, strategy="same_genre")
    │ uses strategy.weights; same scoring pipeline
    ▼
Returns recommendation with possible genre_filter_empty warning
```

## Affected files

- `src/xfinaudio/recommendation/strategies.py` — add `same_genre` profile.
- `src/xfinaudio/recommendation/playlist_service.py` — pass anchor genres and apply pre-scorer filter when strategy requires it.
- `src/xfinaudio/recommendation/prep_copilot.py` or `playlist_service.py` — add helper to extract dominant anchor genre.
- `src/xfinaudio/library/models.py` — verify `genre` is already accessible.
- `tests/test_playlist_strategies.py` — register the new strategy.
- `tests/test_playlist_service.py` — add tests for the genre filter.
- `tests/test_main_window.py` — verify the strategy combo count.

## Safety

- No audio mutation.
- No DSP scope expansion.
- No live Serato Database V2 writes.
- The new strategy is opt-in; other strategies are unchanged.
