# DJ Set-Programming Techniques — Community-Validated Research for XfinAudio

Status: research only. No source, test, doc, or translation file was modified; no commit was made.
Scope: set *preparation/programming* techniques (not live-only performance tricks) that are used by working
professional DJs, corroborated by community experience, and **not** already implemented in XfinAudio.

## 1. Method and sources

Tooling actually used for this research:

- `agent-reach doctor --json` (agent-reach skill, `/Users/freddymolina/.agents/skills/agent-reach/SKILL.md`).
  Backends reported available: `web` (Jina Reader, status ok), `rss`, `github`, `youtube`, `v2ex`, `xiaoyuzhou`.
  Backends reported **unavailable**: `exa_search` (Exa not configured in mcporter), `reddit`/`facebook`/`instagram`/
  `xiaohongshu` (OpenCLI installed but the Chrome extension is not installed), `linkedin` (off), `xueqiu` (login).
- Web search and page reads: DuckDuckGo HTML endpoint and target pages, both read through Jina Reader
  (`https://r.jina.ai/<url>`).
- Reddit: `reddit.com` pages returned HTTP 403 / "blocked by network security" through Jina Reader, and
  `rdt`-cli is not installed. Reddit content was therefore retrieved through the public PullPush mirror of the
  Reddit API (`https://api.pullpush.io/reddit/search/...`), and is cited by its canonical `reddit.com` permalink.
  This is stated explicitly because it is a retrieval route, not the primary source.

Source-quality caveat: web search for these terms returns a large volume of machine-generated "DJ guide" sites
(for example `sfconservatoryofdance.org`, `phaso.io`, `vibesdj.io`, `edm-ghost-production.com`, `setflow.app`,
`mixgraph.io`, `riddimdjpro.com`, `musicianstool.com`). Those were deliberately **not** used as evidence. The
corpus below is restricted to practitioner publications with named authors (DJ TechTools, Digital DJ Tips,
Mixed In Key), working-DJ forums, and Reddit threads with visible community votes/replies.

## 2. Baseline: what XfinAudio already does (excluded from the findings)

Verified by reading the repository (read-only), so that nothing below duplicates existing behaviour:

| Already implemented | Where |
|---|---|
| Camelot compatibility scoring, wheel neighbourhoods, key-shift explanations | `src/xfinaudio/recommendation/camelot.py`, `scoring.py` |
| Camelot tricks (+2 boost, -1 drama, +7 mood shift), fuzzy harmonic matching | `src/xfinaudio/recommendation/scoring.py` |
| Phrase mixing through per-track `energy_in` / `energy_out` / `energy_peak` | `src/xfinaudio/library/models.py`, `scoring.py` (`effective_energy_delta`) |
| Half/double-time BPM handling, BPM adjacency gates and windows | `optimizer.py` (`_lazy_bpm_neighbors`) |
| Acapella/instrumental (version) grouping, duplicate collapse | `candidate_pool.py` (`playlist_duplicate_group_key`) |
| Perceived-energy arc with a main peak about two thirds in and a release at the end | `recommendation/energy_arc.py` (`_PEAK_POSITION = 0.68`) |
| Loudness bands, spectral cohesion, danceability signals | `scoring.py`, `audio/loudness*.py`, `audio/spectral_profile.py` |
| Read-only Serato history/crates aggregation (play count, last played, crate count) as an inert-by-default familiarity signal | `recommendation/familiarity.py`, `exporting/serato_history.py` |
| Strategy profiles (`warmup`, `build`, `peak_time`, `chill`, `same_energy`, `same_genre`, …) as weight/range presets | `recommendation/strategies.py` |

Two consequences for the reading below:

- "Peak around two thirds, then release" is **already implemented** at the whole-set level, so it is not reported
  as a new technique. What the sources add beyond it is *interior* structure: valleys, blocks, and role quotas.
- A play-count/last-played signal **already exists**, but it is oriented as a *familiarity preference*. The
  rotation technique below is about the opposite policy (novelty, cross-DJ overlap), so it is reported as a
  distinct, still-absent capability — with that overlap stated honestly.

---

## 3. Findings

### T1. Triads / tandas — pre-validated 3–4 track clusters with rehearsed transitions

**What it is.** Instead of treating a set as a chain of pairwise-good transitions, professionals maintain a
personal library of short, pre-rehearsed *clusters* (2–4 tracks that were actually played together and whose
transitions were checked by ear). A prepared set is then assembled from these clusters, not from raw tracks.

**Why it works.** A transition between two tracks is not a property of the pair alone: it depends on where the
mix happens and how the phrase, bass, and vocal elements align in *that* order. Validating a cluster in rehearsal
converts an unbounded pairwise-search problem into a much smaller set of reusable, verified objects, and it
guarantees that every junction the DJ will actually perform has already been heard.

**How professionals use it.**
- DJ TechTools, *Reading A Dance Floor* (Teo Tormo, 2018-01-08): triads are "three consecutive songs that work
  well together"; "A triad should usually have songs with the same genre, tempo, and intensity. More importantly,
  you should have already rehearsed 'power transitions' between them. After each 'triad' it's okay to let people
  breathe a bit." The article advises grouping the tracks you already know work into triads, and warnings that
  "Don't play the same groups of songs each week – the regulars notice."
  <https://djtechtools.com/2018/01/08/reading-dance-floor-important-dj-skill/>
- Independent corroboration from a different tradition: tango DJ programming uses *tandas* (rehearsed 3–4 track
  blocks): "Prepare your tandas in advance, but be ready to change everything based on what the floor tells you."
  <https://tangolife.london/blog/energy-waves-creating-peaks-and-valleys-throughout-the-evening>
- Community practice of pre-built blocks: an r/DJs multi-genre DJ describes making "many many crates of mini-sets
  of tunes" when prepping a gig.
  <https://reddit.com/r/DJs/comments/rasvup/tips_for_freestyling_a_multigenre_set/>
- The chapter-based set breakdown posted to r/DJs is the same idea at a coarser grain: three-track groups that
  share "a job to do in the overall story".
  <https://reddit.com/r/DJs/comments/1qwji0c/how_i_structure_sets_using_chapters_a_breakdown/>

**XfinAudio implementation surface.** No cluster/block concept exists in the engine (`triad`, `chapter`, `block`
do not appear in `src/xfinaudio`). Feasible with existing data: the pairwise component scores already computed by
`scoring.score_transition` can be aggregated over a sliding window of 3 to produce a *cluster* score, and
`optimizer.py` already consumes an `arc` bonus matrix, so a cluster bonus is structurally analogous. The genuinely
new data is a *provenance/confidence* flag — "these N tracks were rehearsed or played together" — which could live
in `TrackRecord.tags`/`raw_metadata` or as a new `Playlist`-level record, not as new audio analysis.

**Sources.** DJ TechTools (2018) as above; tangolife.london (independent tradition); Reddit r/DJs threads
`rasvup` (16 points) and `1qwji0c` (27 points).

**Confidence.** **Consolidated.** The naming (triad/tanda/mini-set) comes from a single author (DJ TechTools, 2018),
but the underlying object — rehearsed short blocks reused as set building units — recurs independently in tango
programming and in two Reddit threads.

---

### T2. Vocal spacing — vocal-density budget across the set

**What it is.** Vocals are treated as a scarce, high-attention resource: they are spread through the set, never
clustered, and separated by instrumental (or non-vocal) tracks. A programmer effectively budgets vocal density
per hour rather than shuffling vocals randomly.

**Why it works.** A vocal is the most salient, most memorable element of a track and it dominates the attention
budget of a room. Two vocals in a row compete with each other (the second is heard as "more of the same" instead
of as a moment), and a set saturated with vocals loses dynamic contrast because the melodic content never drops
away. Spacing them makes each one land, and gives the crowd the sing-along moment the sources describe.

**How professionals use it.**
- Ferry Corsten, via Digital DJ Tips, *Choosing Tracks For A DJ Set: Start With The Story, Not The Mix*
  (Digital DJ Tips staff write-up, last updated 2026-05-01): "Trance is largely instrumental, but vocals are
  powerful when they land in the right place. **The mistake is clustering them together.** Space them out — a
  couple of instrumentals, a vocal, a couple more instrumentals — and each one becomes a moment."
  <https://www.digitaldjtips.com/how-to-choose-tracks-ferry-corsten/>
- DJ TechTools, *Controlling the dancefloor: a guide on organizing playlists by energy* (Vibralocity, Kyle Mohr,
  2022-11-25) lists the axis the author explicitly sorts by after BPM and key: "arranging by BPM first, followed
  by key, energy level, **vocals**, and genre" — i.e. vocals is a first-class programming column for a working DJ.
  <https://djtechtools.com/2022/11/25/controlling-the-dancefloor-a-guide-on-organizing-playlists-by-energy/>
- Community validation of the failure mode: the r/Drumcode thread *Too many vocals in sets* is a listener-facing
  complaint about precisely this: "many of the tracks relied on edited/chopped up vocals… Heavy reliance on vocals
  to carry the set"; top replies include "i miss tracks without vocals".
  <https://www.reddit.com/r/Drumcode/comments/1d0hkh9/too_many_vocals_in_sets/>
- Adjacent, from the production side: producer advice to leave melodic space — Mixed In Key, *Control The Energy
  Level*: avoid overlaying a beat on the breakdown, "if you keep this section melodic… this gives people room to
  breathe." <https://mixedinkey.com/blog/control-the-energy-level/>

**XfinAudio implementation surface.** There is **no vocal field anywhere** — `grep -ri vocal src/xfinaudio` returns
nothing. New metadata is required; realistically a boolean/tri-state (`instrumental` / `vocal` / `vocal-hook`) or a
numeric vocal-density tag. Mixed In Key does not emit this, so it would have to come from a user/bookmark tag,
a `grouping`/`comment` convention, or an optional analysis pass. Engine touch points: a penalty term in
`scoring.py` for adjacent high-vocal tracks, and a window constraint in `optimizer.py`; a `vocal_density` budget
would be a natural companion to the existing `energy_arc` shape constraints. The design must degrade cleanly to
"unknown" (`metadata_status`) rather than assume a missing tag means instrumental.

**Sources.** Digital DJ Tips (Ferry Corsten lesson); DJ TechTools (energy-playlist article); Reddit r/Drumcode
thread; Mixed In Key (adjacent production rationale).

**Confidence.** **Consolidated** for "do not cluster vocals"; the specific spacing ratio ("a couple of
instrumentals, a vocal") is **single-source** (Ferry Corsten).

---

### T3. Runtime budgeting — fill the slot by minutes, then land the last track

**What it is.** Set preparation starts from two numbers: how long the slot is and how many tracks therefore fit.
The programmer builds to a total wall-clock runtime, plans where the final track lands, and accepts that track
*count* is a derived number, not the input.

**Why it works.** It is the only way to guarantee the ending is a decision instead of an accident. It also
controls pacing: the same 20 tracks can be a 60-minute set or a 100-minute set depending on how long each track is
allowed to run, so runtime budgeting is the knob that sets the *average* track dwell time — the single biggest
driver of perceived density.

**How professionals use it.**
- Ferry Corsten (Digital DJ Tips): "Ferry's first question isn't 'which tracks?' – it's 'how long am I playing?'
  Knowing your set length determines how many tracks you can actually fit in… Typically, a one-hour set tends to be
  around 13-14 tracks for Ferry. When asked to prepare something in the 60-90 minute range for this course, he dug
  through his catalogue and landed on 19." And on why it matters: "the last thing you want is the stage manager
  cutting you off right when the crowd expects that final moment. Know your track count, and your set ends on your
  terms." <https://www.digitaldjtips.com/how-to-choose-tracks-ferry-corsten/>
- Community spread (r/DJs, *How many tracks do you average in a one hour set?*, 68 points): the OP ran 22–26 tracks
  per hour at ~90s–2min each; replies ranged from "20 to 30 tracks for an hour" (techno, "double that for a two-hour
  set") through "Average 30-40 per hour" to "between 55 and 70 tracks in 1h for tech house, house, bass house".
  <https://www.reddit.com/r/DJs/comments/q19e78/how_many_tracks_do_you_average_in_a_one_hour_set/>
- The same thread contains the pacing caveat that matters for an optimizer: "build some variation in it, some
  quick mixes and some longer tracks, otherwise it gets predictable."
- DJ TechTools names the opposite failure ("mixing really fast to the next track" when the floor is enjoying a
  track) as a symptom of a set going wrong: "letting songs play long enough".
  <https://djtechtools.com/2018/01/08/reading-dance-floor-important-dj-skill/>
- Mixed In Key states the same problem from the mixing side: playing every track to its full length "so your
  crowd might start to get bored". <https://mixedinkey.com/blog/control-the-energy-level/>

**XfinAudio implementation surface.** `TrackRecord.duration` already exists and a *count* limit already exists
(`prep_copilot.Intent.target_track_count`, default 25, used by `_limit_recommendation`). What is missing is a
**runtime** budget: `target_minutes` in `DJControls`/prep intent, a runtime accumulator in `optimizer.py`, and a
pacing variance term so the optimizer does not converge on identical dwell times. No new metadata.

**Sources.** Digital DJ Tips (Ferry Corsten); Reddit r/DJs `q19e78`; DJ TechTools (2018); Mixed In Key.

**Confidence.** **Consolidated** that runtime is the planning input; the *counts per hour* are strongly
**context-dependent** (13–14/h for trance sets vs. 55–70/h for tech house), so any default must be
genre/strategy-relative rather than global.

---

### T4. Slot-role and venue-profile programming (warm-up / peak / closing; arrival and exit times)

**What it is.** A set is prepared against the *role it plays in the night* — opening, warm-up, lead-in to a
headliner, peak hour, closing — plus a venue profile (when people actually arrive, when the room peaks, when it
empties, whether people come to dance or to talk). Different roles imply different starting points, density, and
endings.

**Why it works.** Energy has no absolute meaning; it is relative to what the room expects at that time. The same
track is a build-up at 23:00 and a mistake at 01:30. Programming against the room's time profile aligns the set's
shape with the room's readiness curve instead of with the DJ's own taste.

**How professionals use it.**
- DJ TechTools, *Reading A Dance Floor*, gives an explicit venue-scouting checklist to use *before* selecting
  music: "Typically, what is the expected vibe at different times of night?", "When do people actually start to
  arrive?", "What time does the vibe/music/attendance peak, and then when do people start to leave?", "Do people
  come to this club to talk and socialize, or are they going just for dancing?" And: "the more you find out, the
  better pre-selection of music you'll be able to do for your gig."
  <https://djtechtools.com/2018/01/08/reading-dance-floor-important-dj-skill/>
- DJ TechTools forum, *Structuring your set* — a working DJ states the role dependency directly: "Structuring a
  set depends totally on what my roll/position is in the programming for the party. I've done everything from
  opening a night, lead in to the headliner, headliner… All these require different structuring of your mix and
  music selection." <https://forum.djtechtools.com/t/structuring-your-set/45716>
- Digital DJ Tips answers a 4-hour-slot question in those same terms, structuring the night as "warm-up,
  transitional, and peak tracks" and warning "Don't panic and play all your good tunes because people aren't
  dancing – early doors is a game of patience."
  <https://www.digitaldjtips.com/your-questions-how-do-i-keep-a-4-hour-dj-set-interesting/>
- Same principle from tango programming: "The peak hour is your opportunity to create magic… Your strongest tandas
  should land here." <https://tangolife.london/blog/energy-waves-creating-peaks-and-valleys-throughout-the-evening>

**XfinAudio implementation surface.** `strategies.py` already ships `warmup`, `build`, `peak_time`, `chill`, but
these are weight/filter presets applied to a whole recommendation, not a *role sequence*. A first-class
`slot_role` (per-position role label with quotas, e.g. opening→warm-up→build→peak→close) and a
`venue_profile` (slot length, expected peak position, expected exit behaviour, dance-vs-talk) would be new inputs
on the prep intent / `DJControls`, then implemented as an additional target curve in `energy_arc.py`-style shape
terms plus role-gating in `candidate_pool.py`. No new per-track metadata; `duration` plus energy are the signals.

**Sources.** DJ TechTools (2018); DJ TechTools forum (2012); Digital DJ Tips (2011/2017); tangolife.london.

**Confidence.** **Consolidated.** Multiple independent working DJs describe role-dependent structuring; only the
venue-timing checklist is a single authored list.

---

### T5. Floorfiller reserve — hold the anthems for later, and let familiarity rise

**What it is.** The biggest, most recognizable tracks ("floorfillers", "bangers", "classics") are deliberately
*withheld* from the early part of a set and spent later, in the third/fourth act or the peak. Familiarity, not
raw energy, is the axis that rises over the night.

**Why it works.** Recognition is a finite resource that produces a disproportionate reaction. Spending the
recognizable tracks early leaves the rest of the night with nothing to escalate to, and it re-exposes the same
tracks if the DJ repeats them later. Holding them converts each one into a peak, and the audience's own
familiarity curve compounds the effect as the crowd grows.

**How professionals use it.**
- DJ TechTools, *Reading A Dance Floor*, describes a four-act structure with explicitly reserved material:
  first act "keep it fairly linear, maintain a stable tempo and energy level, and try not to play too many classic
  tracks or floorfillers"; second act "a few floorfillers are welcome now"; third act, at its end, "take everything
  to a high point of tempo and intensity"; fourth act "Reward those who have endured… release the hits and
  floorfillers that remain in your playlists."
  <https://djtechtools.com/2018/01/08/reading-dance-floor-important-dj-skill/>
- Working DJs on the DJ TechTools forum agree in one voice: "never never never ever play the big bangers when the
  night is still early. nothing worst than repeating a track later in the night."
  <https://forum.djtechtools.com/t/structuring-your-set/45716>
- Digital DJ Tips: "Familiarity is a big thing – as the night moves on, tunes your audience is more familiar with
  ought to be played", together with the patience rule quoted in T4.
  <https://www.digitaldjtips.com/your-questions-how-do-i-keep-a-4-hour-dj-set-interesting/>
- Mixed In Key gives the timing reason from the mixing side: "In general, it's a good idea to mix out of the chorus
  so the crowd hears the most familiar part of the song."
  <https://mixedinkey.com/blog/control-the-energy-level/>

**XfinAudio implementation surface.** Energy is already modelled, but **recognizability is not**. Needs a
per-track signal for "anthem/classic/floorfiller" or a *familiarity* value — the machinery for the latter partly
exists (`recommendation/familiarity.py` aggregates Serato `play_count`/`last_played`), so the new work is a
*policy* that (a) constrains such tracks out of the opening third and (b) ranks a rising familiarity target over
position, in the same shape-terms style as `energy_arc.py`. A tag-based fallback (`tags`/`grouping`) is the
low-cost option; audio-derived recognizability is out of scope for this application.

**Sources.** DJ TechTools (2018); DJ TechTools forum (2012); Digital DJ Tips (2011/2017); Mixed In Key.

**Confidence.** **Consolidated.** The reserve principle is stated independently by the publication, the forum DJs,
and Digital DJ Tips; the tango source states the same thing as "your strongest tandas should land" in the peak hour.

---

### T6. Rotation and cross-DJ overlap avoidance (artist diversity, no repeats, previous DJ's history)

**What it is.** Three related constraints applied at preparation time: do not play the same track twice in one
set; watch how recently each track was played in previous gigs; and check what the DJ before you already played so
you do not repeat their tracks. A subset of the community extends this to "one track per artist per set".

**Why it works.** For a recurring audience, the *same* track on consecutive gigs reads as a limited library, and
the regulars and staff notice before the average customer does. Repetition also forecloses the escalation
described in T5: once the anthem is spent, it cannot be a peak again.

**How professionals use it.**
- DJ TechTools, *The Regulars Notice: How To Avoid Playing The Same DJ Set Every Week* (2017-09-04) is entirely
  about prep-time tracking: "Being aware of the last time you played your tracks is the easiest way to identify the
  problem. While DVS software like Traktor and Serato and even RekordBox USB drives all maintain a history, it's
  only useful if you look at it and compare your sets week to week." The author documents a manual rotation scheme
  (marking played tracks `a1`, `a2`, … in the Serato `Grouping` column) and a deliberate novelty quota: "Periodically
  I would even challenge myself to play an entire hour without using a single track I had played before."
  He also warns that per-track "good transitions" comments turn into "a DJ-by-numbers pattern".
  <https://djtechtools.com/2017/09/04/regulars-notice-avoid-playing-dj-set-every-week/>
- Digital DJ Tips, *Is It OK To Play The Same Track Twice?* (Christian Yates, last updated 2018-03-23) states the
  rule and the exception: "The best advice I can give here is that if a DJ has already dropped a track you wanted to
  play, tough luck, don't play it, the one exception maybe being the hands-down biggest tune of the moment, played
  one more time at the very end of the night."
  <https://www.digitaldjtips.com/your-questions-is-it-ok-to-play-the-same-track-twice/>
- The reader question in that article carries the artist rule: "I try my best not to repeat the same tracks already
  played by other DJs and I don't use more than one track by the same artist in any of my sets." Note this is
  **contested**: the same article argues that two tracks by one artist back to back "is often the most logical
  progression", and an r/DJs discussion of playing a track twice splits by event type — "if you're playing an actual
  set at a venue 1-2 hour slot then hell fucking no", while turnover-heavy weddings/private events are relaxed.
  <https://www.reddit.com/r/DJs/comments/pwik35/playing_a_song_twice_or_more_in_one_night/>
- Preparing against the previous DJ's set is explicit community practice in that same r/DJs thread: "at least look
  or ask for the history of the dj before you".
- Independent tradition again — tango: "Too much variety: Playing 15 different orchestras in a three-hour milonga
  can feel scattered. Focus on 8-10 orchestras and build coherent tandas from each."
  <https://tangolife.london/blog/energy-waves-creating-peaks-and-valleys-throughout-the-evening>

**XfinAudio implementation surface.** Existing: duplicate/version collapse by title+artist
(`candidate_pool.playlist_duplicate_group_key`) and an inert-by-default `FamiliaritySignal`
(`play_count`, `last_played`, `crate_count`). Missing: (a) a novelty/rotation *policy* (e.g. penalise tracks whose
`last_played` is within N days, or a `novelty_ratio` target), (b) an artist-spread constraint over the ordered set
(new `ScoringWeights`-independent constraint in `optimizer.py`), and (c) an overlap report against a previous
Serato session (the read-only history spike already parses sessions; the reporting surface is new, e.g. a
`dj_readiness`-style finding). Note the polarity question is a product decision: today the signal means
"familiarity preference"; rotation needs the inverse policy — both can coexist as settings.

**Sources.** DJ TechTools (2017); Digital DJ Tips (2018); Reddit r/DJs `pwik35` (44 points); tangolife.london.

**Confidence.** "No repeat within a set, and check the previous DJ's history" is **consolidated**. The
"one track per artist per set" rule is **contested / single-source**, and event-type dependent; it should ship as
an optional constraint, not a default.

---

### T7. Genre pivots through bridge tracks, and stacked genre sections

**What it is.** Genre changes inside a set are engineered rather than avoided: the programmer either links the two
genres through a track that shares a concrete element with both (a "bridge" track, tagged as such in the library),
or stacks genres as ordered sections so the whole set travels through them. Genre tags are also stored *paired*
to record which genres a track can bridge.

**Why it works.** Two tracks from different genres rarely share BPM, so compatibility has to be found on another
axis — a shared drum pattern, bassline, vocal style, or lyric hook. A bridge track contains both vocabularies and
lets the tempo move while the floor's reference point stays stable. Section stacking works for the same reason at
a larger scale: the pivot is amortized over several tracks instead of one.

**How professionals use it.**
- r/Beatmatch, *How can I (subtly) switch between genres in my sets?*: "For me it's about linking some common idea
  in tracks, and finding the tracks that straddle the genres you work with. If both have strong acid elements but
  one is techno and the other is house, the change in beat style is a lot easier to manage. Or if you want to get
  into industrial techno from melodic house, bridge it with melodic techno. I tag my library with this in mind too,
  like: House;Techno." Another reply describes the same technique as a staged hand-off: "start playing crossover
  type music… hip hop music with a super edm type Instrumental… then full edm shit". A third stresses the
  per-transition read: "little shifts (<5% of the BPM) are a good way to adjust the energy" and frames genres as
  "just a collection of attributes". <https://www.reddit.com/r/Beatmatch/comments/t2loel/how_can_i_subtly_switch_between_genres_in_my_sets/>
- r/DJs, *Tips for freestyling a multi-genre set?* (16 points), from a working 4-hour-slot DJ: "the usual rule book
  goes out the window here, BPM ranges can be too wide… I used to play in sections like… pop/rnb → rap → housey
  tunes with rap vocals → commercial house"; and: "when you cross genres know what the bridge is that connects the
  tunes, is it a rhythm, a phrase, bass line, lyrics." <https://reddit.com/r/DJs/comments/rasvup/tips_for_freestyling_a_multigenre_set/>
- Digital DJ Tips gives the same trick with a concrete example: "playing hip hop remixes of pop, house remixes of
  hip hop etc will help you blend between the styles."
  <https://www.digitaldjtips.com/your-questions-how-do-i-keep-a-4-hour-dj-set-interesting/>

**XfinAudio implementation surface.** `genre` and `tags` already exist in `TrackRecord`, and there is a
`same_genre` strategy, but there is no bridge/gradient concept and no section-level genre plan. Needed: (a) a
convention for *multi-genre* tags (the community stores pairs such as `House;Techno` — the current single-`genre`
field plus `tags` can carry this), (b) a scoring relaxation when a cluster is used as a pivot (bridge tracks are
*expected* to be less similar than neighbors, so a naive similarity score punishes exactly the right track), and
(c) a section template so a genre plan is an input rather than an emergent result. Touch points: `scoring.py`
(relaxed/alternative criteria at designated pivot slots), `strategies.py` (genre-section templates),
`optimizer.py` (section boundaries).

**Sources.** Reddit r/Beatmatch `t2loel`; Reddit r/DJs `rasvup`; Digital DJ Tips (4-hour article).

**Confidence.** **Consolidated** for the bridge-track concept (three independent community sources) and
**medium** for the specific genre-section ordering, which is one DJ's practice plus a Digital DJ Tips example.

---

### T8. Multi-tempo anchor lanes — energy is not BPM

**What it is.** Instead of a monotone BPM climb, the set is designed around a few *anchor tempos* (e.g. 110, 128,
150) and moves between them, with the energy of each track judged independently of its BPM. The programmer
therefore buys energy with arrangement density rather than with speed.

**Why it works.** Perceived intensity is driven mostly by how tightly the arrangement is programmed — event
density in the waveform — not by the BPM counter: a 150 BPM spacious track can feel calmer than a dense 128 BPM
track. Decoupling the two axes multiplies the usable library (an entire genre can be reachable from one set
without a forced tempo ramp) and removes the failure mode where a set must either speed up or stay in one lane.

**How professionals use it.**
- Laidback Luke, via Digital DJ Tips, *Energy vs Tempo: Why BPM Doesn't Tell The Whole Story* (last updated
  2026-05-01): Luke "makes the case that energy and tempo are not the same thing" using six tracks: a 110 BPM track
  that is "a hip-shaker but not exactly high-energy", a 128 BPM track that "feels noticeably heavier", and a 150 BPM
  track that is "actually the most spacious and mellow-feeling of the three". "So what actually creates energy in a
  track? Luke points to the programming – how tightly the elements are arranged… the denser and thicker the
  waveform, the more energy a track has, regardless of what the BPM counter says." And on construction: "Luke uses
  110, 128, and 150 as anchor points in his sets, moving between them in ways that let him take his crowd on a
  journey across genres without getting trapped in one tempo lane."
  <https://www.digitaldjtips.com/energy-vs-tempo-luke-lesson/>
- Community corroboration that the peak does not have to be the fastest part, from an r/DJs chapter breakdown
  (27 points): "the BPMs here aren't the highest in the set but the energy is. that's the point – peak energy isn't
  just about speed." <https://reddit.com/r/DJs/comments/1qwji0c/how_i_structure_sets_using_chapters_a_breakdown/>
- DJ TechTools makes the library-organization corollary: perceived energy from analysis tools such as Mixed In Key
  "rarely will tell you how the song will perform when it is being played for a dancefloor".
  <https://djtechtools.com/2022/11/25/controlling-the-dancefloor-a-guide-on-organizing-playlists-by-energy/>

**XfinAudio implementation surface.** BPM gates (`optimizer._lazy_bpm_neighbors`) and the energy axis already
exist, and half/double-time is handled — so this is **not** a request for tempo handling. What is absent is
(a) treating *anchor BPMs* as a planning input, and (b) an energy proxy independent of BPM beyond the existing
energy field. The latter already has partial support from the audio side (`danceability_profile`,
`spectral_profile`, `loudness_profile` are analysed per track) — an arrangement-density signal derived from
existing spectral/danceability data would be the honest way to implement Luke's "density" claim without new audio
analysis. Touch points: `candidate_pool.py` (anchor lanes as pool stratification), `scoring.py`
(energy/BPM decoupling), `strategies.py` (anchor-lane presets). **Caution:** the "denser waveform = more energy"
claim is a practitioner heuristic, not a validated psychoacoustic formula; it should ship as an additional
displayed signal, not as a silent replacement for the existing energy field.

**Sources.** Digital DJ Tips (Laidback Luke lesson, 2026); Reddit r/DJs `1qwji0c`; DJ TechTools (2022).

**Confidence.** **Medium.** The energy≠BPM distinction is stated by one very high-profile practitioner and echoed
by the community; the anchor-lane *construction method* is single-source.

---

### T9. Contingency branches — pre-built escape hatches and safe floor-fillers

**What it is.** Preparation produces not one path but a small set of pre-validated alternatives at known anchors:
clusters that reliably fill a floor, and pre-checked "get out of trouble" transitions that allow an immediate
exit from a track that is not working. The prepared set is treated as a starting point rather than a script.

**Why it works.** Live failures are usually failures of *recovery speed*, not of taste. A DJ who must search a
library mid-transition loses the floor during the search. Pre-validating alternatives turns a slow search into a
fast decision, and it also makes the prepared plan less brittle: deviating no longer means abandoning the plan.

**How professionals use it.**
- DJ TechTools, *Reading A Dance Floor*, troubleshooting section: when the floor empties, "forget about the rules.
  Mix out as soon as you can into a safe floor filler", and (for a crowd that is present but inert) "you might need
  to adjust your intensity… and give your crowd a break before restarting a ramp up to an intensity peak."
  The same article recommends building "established batches of songs that work well together" in advance.
  <https://djtechtools.com/2018/01/08/reading-dance-floor-important-dj-skill/>
- The r/DJs multi-genre thread describes exactly the prep artifact: "When I am prepping for a gig, I'll make many
  many crates of mini-sets of tunes."
  <https://reddit.com/r/DJs/comments/rasvup/tips_for_freestyling_a_multigenre_set/>
- Tango programming states the flexibility requirement in the same terms: "Plan but stay flexible: Prepare your
  tandas in advance, but be ready to change everything based on what the floor tells you. The prepared set is a
  starting point, never a rigid script."
  <https://tangolife.london/blog/energy-waves-creating-peaks-and-valleys-throughout-the-evening>

**XfinAudio implementation surface.** The engine returns one optimized sequence; there is no branching API.
A natural, low-risk implementation is not a new optimizer but an *alternative recommendation* surface: from a
given anchor track or slot, ask for the N best continuations (or the best cluster) under the same scoring, and attach
them to the recommendation as named branches ("safe filler", "hold", "lift"). This reuses
`optimizer.recommend_sequence` with `start_path`/`locked_paths` (both already exist in `DJControls`) rather than
adding a new search. Display/export surface: review screen and playlist export only.

**Sources.** DJ TechTools (2018); Reddit r/DJs `rasvup`; tangolife.london.

**Confidence.** **Consolidated** that pre-built fallbacks are professional practice; **single-source** for the
specific "safe floor filler" wording (DJ TechTools).

---

### T10. Interior valleys and breakdown-density balance (scheduled breathers)

**What it is.** Deliberate mid-set energy *drops* — a valley that lets the room rest — scheduled as part of the
structure, plus a check on how many "breakdown-heavy" tracks sit in a row. Peaks are treated as something that
must be *earned* by a preceding release.

**Why it works.** Sustained maximum intensity produces adaptation and fatigue, so an unreleased build stops
reading as a build. A drop restores contrast, which is what makes the following peak perceptible; a track that is
all breakdown and no drop wastes time the floor is ready to spend.

**Overlap warning (important).** XfinAudio already models a whole-set arc with a peak about two thirds in and a
release at the end (`recommendation/energy_arc.py`), and the parent's already-implemented list includes "contrast
injection". This finding is therefore *narrower* than the implemented features and must not be read as a
re-request: it is about (a) **interior** valleys (more than one release per set, on a schedule, not only at the
end), (b) **block-level** shape (a valley that is a whole chapter, not one contrast track), and (c) a
**breakdown-density** constraint rather than a per-transition contrast bonus. See also T1, whose sources bundle the
breather with the block ("After each 'triad' it's okay to let people breathe a bit").

**How professionals use it.**
- Mixed In Key, *Control The Energy Level*: "In any DJ set, ebb and flow is crucial… Transporting a crowd to dizzy
  heights and then bringing everyone down for a breather is an essential skill, and it's all about energy control";
  "we like to think of rhythm as a landscape with peaks and valleys. At the peaks, you're telling your audience when
  to get excited; at the valleys, you're giving them a chance to breathe." It also gives the arrangement rationale:
  "Varying levels of intensity are also essential elements in dance music… intro > normal intensity > high intensity
  > breakdown > high intensity > outro." <https://mixedinkey.com/blog/control-the-energy-level/>
- DJ TechTools forum, *Structuring your set*: one DJ describes the loop directly — "Ill build the energy for a few
  songs, and once everyone is tired (including me) Ill drop a long epic vocal to calm it down. then slowly build
  back the energy from there, rise and repeat for majority of the night"; another draws the shape: "Last 3-4 tracks
  are always the massive toe curlers and last tune brings us down to earth. think of an 'S' turned on its side."
  <https://forum.djtechtools.com/t/structuring-your-set/45716>
- The r/DJs chapter breakdown names the release as the thing most people skip and the thing that makes peaks work:
  "this is the part most people skip but it's what makes peaks actually hit. you need contrast… dropping the BPM
  slightly and the intensity more. creates tension because the room can feel something bigger is coming."
  <https://reddit.com/r/DJs/comments/1qwji0c/how_i_structure_sets_using_chapters_a_breakdown/>
- DJ TechTools, *Reading A Dance Floor*, on the empty-floor diagnosis: "You might have burned out people with
  excessive intensity (often during the second or third act). You might need to adjust your intensity… and give
  your crowd a break before restarting a ramp up to an intensity peak. This time do not go as fast as before."
- Independent tradition: "Build waves of intensity, allow brief breathing spaces, then build again."
  <https://tangolife.london/blog/energy-waves-creating-peaks-and-valleys-throughout-the-evening>

**XfinAudio implementation surface.** Extend `energy_arc.py` from a single-peak shape to a parameterized
multi-valley shape (number of waves and depth), and add a windowed constraint in `optimizer.py` limiting
consecutive "breakdown-dominant" tracks. The arrangement signal exists in part: per-track `energy_in`/`energy_out`/
`energy_peak` already describe entry/exit/peak, which is enough to detect "starts high, dips, ends high" patterns
without new audio analysis.

**Sources.** Mixed In Key; DJ TechTools (2018); DJ TechTools forum (2012); Reddit r/DJs `1qwji0c`; tangolife.london.

**Confidence.** **Consolidated** for interior valleys/ebb-and-flow, including an authoritative-vendor statement
(Mixed In Key). Breakdown-density as a *constraint* is inferred from the same sources plus a common community
complaint, and is the weakest of the three sub-claims.

---

### T11. Harmonic-variety guardrail (weakly sourced)

**What it is.** A guardrail against over-applying harmonic rules: strict, tag-following Camelot chains across a
whole set homogenize the sound, so the programmer deliberately breaks the chain or uses the wider set of key
relationships instead.

**Why it works.** If BPM range, venue suitability, and floor response already narrow the library, adding a rigid
key rule narrows it again — the set converges on a narrow sonic band. Perceptually, a well-mixed key change is
often acceptable when the phrasing is right, so the constraint is softer than the rule set implies.

**How professionals use it.**
- DJ TechTools, *The Regulars Notice*: "Don't misunderstand, harmonic mixing is incredibly important if you want
  your transitions to sound good. What isn't good is scanning your entire library with key detection software and
  then sticking religiously to 1A -> 2A -> 2A -> 2B -> 3B -> 3A -> 4A style transitions… you're more likely to
  homogenize your sound."

**XfinAudio implementation surface.** A *diversity* term (or a soft floor on distinct keys/modulations per set /
per block) alongside the existing harmonic weights, plus a warning when a recommendation's key spread is narrower
than a threshold. This is a measurement and reporting feature before it is a scoring feature, and it pairs with
the already-observed compression problem documented in `energy_arc.py` (a set that "ran 25 tracks without leaving
level 7").

**Sources.** DJ TechTools (2017) only.

**Confidence.** **Weakly sourced / single-source.** Included because it is a directly stated, specific caution
from a practitioner publication about the exact mechanism XfinAudio optimizes (Camelot chains), and because it is
testable, not because the community has validated it broadly.

---

## 4. Ranked feasibility table

Ranked by (value for set programming) relative to (new data required) and (confidence).

| # | Technique | Data needed | Engine touch point | Value for sets | Confidence |
|---|---|---|---|---|---|
| 1 | T1 Triads / rehearsed clusters | Pairwise scores (existing) + a cluster/"played-together" flag (tags or playlist record) | `scoring.py` windowed aggregate, `optimizer.py` cluster bonus (arc-bonus-shaped) | High — improves the actual junctions, not just the track list | Consolidated |
| 2 | T3 Runtime budgeting | `duration` (existing) | `prep_copilot` intent / `DJControls` (`target_minutes`), `optimizer.py` accumulator + pacing variance | High — makes the ending a decision; controls density | Consolidated |
| 3 | T2 Vocal spacing | **New** vocal/instrumental signal (tag convention or optional analysis) | `scoring.py` adjacency penalty, `optimizer.py` window constraint | High — removes a common, audible failure | Consolidated (ratio single-source) |
| 4 | T4 Slot-role / venue profile | `duration`, energy (existing) + new intent inputs (slot length, expected peak, arrive/exit times, role) | `prep_copilot`/`DJControls`, `energy_arc.py` role curves, `candidate_pool.py` role gating | High — makes one recommendation correct for one gig | Consolidated |
| 5 | T5 Floorfiller reserve | New "anthem/classic" or familiarity value; existing `FamiliaritySignal` usable as a proxy | `energy_arc.py`-style position target, `candidate_pool.py` opening-third gate | High — protects the arc's top end | Consolidated |
| 6 | T9 Contingency branches | Existing (reuses `start_path`/`locked_paths`) | `optimizer.recommend_sequence` called per branch; review screen + export only | Medium-high — resilience without new optimization theory | Consolidated (wording single-source) |
| 7 | T7 Genre bridges and sections | `genre` + `tags` (existing), multi-genre tag convention | `scoring.py` pivot relaxation, `strategies.py` section templates, `optimizer.py` boundaries | Medium-high — unlocks cross-genre libraries | Consolidated (bridge) / medium (sections) |
| 8 | T6 Rotation / cross-DJ overlap | Existing Serato `play_count`/`last_played`; new policy + report | `familiarity.py` policy inversion, `candidate_pool.py` novelty, `dj_readiness`-style overlap report | Medium-high for residencies; low for one-off gigs | Consolidated (no-repeat, history) / contested (artist rule) |
| 9 | T10 Interior valleys / breakdown density | `energy_in/out/peak` (existing) | `energy_arc.py` multi-valley parameterization, `optimizer.py` windowed constraint | Medium — sharpens an implemented feature rather than adding one | Consolidated (valleys) / weak (density) |
| 10 | T8 Multi-tempo anchor lanes | Energy (existing) + better density proxy from `danceability`/`spectral` data | `candidate_pool.py` anchor stratification, `scoring.py` energy/BPM decoupling | Medium — broadens usable library | Medium |
| 11 | T11 Harmonic-variety guardrail | Existing keys | `scoring.py` diversity term / quality report | Low-medium — a safety net against over-optimization | Weak / single-source |

## 5. Well-supported vs weakly sourced

**Well-supported (multiple independent sources, at least one named practitioner publication):**

- T1 triads / tandas / mini-sets (DJ TechTools 2018 + tango programming + two r/DJs threads).
- T2 "do not cluster vocals" (Ferry Corsten via Digital DJ Tips + DJ TechTools' use of vocals as a sort axis +
  the r/Drumcode listener complaint; Mixed In Key supports the underlying "leave melodic space" rationale).
- T3 runtime as the planning input (Ferry Corsten via Digital DJ Tips + DJ TechTools + Mixed In Key + r/DJs).
- T4 slot-role programming (DJ TechTools article + DJ TechTools forum + Digital DJ Tips + tango).
- T5 floorfiller reserve / rising familiarity (DJ TechTools article + DJ TechTools forum + Digital DJ Tips +
  Mixed In Key).
- T6 no-repeat-in-a-set and check-the-previous-DJ's-history (DJ TechTools 2017 + Digital DJ Tips + r/DJs +
  tango artist-spread).
- T7 bridge tracks (r/Beatmatch + r/DJs + Digital DJ Tips).
- T9 pre-built fallbacks and safe floor-fillers (DJ TechTools + r/DJs + tango).
- T10 ebb and flow / valleys (Mixed In Key + DJ TechTools article & forum + r/DJs + tango).

**Weakly sourced (single source or contested):**

- T8 anchor-tempo lanes — one practitioner lesson (Digital DJ Tips/Laidback Luke), community-echoed for the
  "peak isn't the fastest point" half only.
- T11 harmonic-variety guardrail — a single DJ TechTools article, no community corroboration found.
- T6's "one track per artist per set" rule — explicitly contested: Digital DJ Tips argues back-to-back tracks by
  one artist are often the most logical progression, and r/DJs splits by event type. Do not ship as a default.
- T10's breakdown-density *constraint* — inferred from the same sources as the valleys claim; no source states a
  numeric rule, and one DJ TechTools forum thread on the topic was not usable as evidence (see below).
- T2's exact spacing ratio ("a couple of instrumentals, a vocal") — Ferry Corsten only.
- T5's "recognizability" signal — the principle is consolidated, but no source specifies how to compute a
  floorfiller score from metadata; that mapping is an XfinAudio design decision, not a researched fact.

## 6. What could not be verified

- **Reddit primary interface blocked.** Direct `reddit.com` reads returned HTTP 403 through Jina Reader and the
  agent-reach Reddit backend (OpenCLI) is unusable without a Chrome extension, so Reddit evidence comes from the
  PullPush mirror of the Reddit API. Vote counts and comment text were retrieved from that mirror; ranking within a
  thread may not exactly match what a logged-in user sees today.
- **No quantitative community studies were found.** Every technique here is practitioner or community testimony.
  There is no dataset in the retrieved corpus measuring, for example, the effect of vocal spacing or triad reuse on
  crowd retention. Confidence below therefore describes *source agreement*, never measured effect size.
- **Excluded low-quality material.** Several highly-ranked search results were machine-generated "DJ guide" sites
  with no named author or community backing (listed in §1). Their claims were not used, and some of them restate
  the same techniques — the presence of unverifiable duplicates is not counted as corroboration.
- **Not retrieved.** A DJ TechTools forum thread on breakdown-heavy sets and a Metal/Drumcode thread on vocal
  fatigue were surfaced by search but produced no readable content through the available routes, so the
  breakdown-density and vocal-fatigue claims rest only on the sources cited above.
- **No audio-side validation.** Whether any of these can be inferred from the audio analysis already present in
  XfinAudio (`danceability_profile`, `spectral_profile`, `loudness_profile`, edge spectral data) was not tested;
  T8 in particular needs a spike before it is treated as implementable without new metadata.
