# Specification: Genre-Stable Playlist Routing

## Requirements

### R1. New "Same Genre" strategy

**GIVEN** the recommendation strategy registry  
**THEN** `same_genre` is registered alongside existing strategies.

### R2. Genre pre-scorer filter

**GIVEN** anchor tracks with primary genre `world_latin`  
**WHEN** `recommend_playlist` runs with strategy `same_genre`  
**THEN** only tracks whose primary genre matches `world_latin` are eligible.

**GIVEN** no candidate tracks match the anchor genre  
**WHEN** `recommend_playlist` runs with strategy `same_genre`  
**THEN** the recommender falls back to unfiltered scoring and the result includes a `genre_filter_empty` warning.

### R3. Score and warnings are deterministic

**GIVEN** the same inputs (records, strategy, controls)  
**WHEN** `recommend_playlist` runs twice  
**THEN** the recommendation order and warnings are identical.

### R4. Symmetric with Same Color

**GIVEN** the strategies `same_genre` and `same_color`  
**THEN** both use the same internal pre-scorer filter pattern and both keep the existing scoring pipeline.

## Non-functional

- The change must not break existing strategy tests.
- The change must stay within the 400-line review budget.
