# Scientific Literature for the XfinAudio Engine — Peer-Reviewed and Preprint Evidence

Status: research only. Exactly one file was created (`odd/research/scientific-papers-mixing.md`); no source, test,
config, translation, or other artifact was modified, and nothing was committed. This is the second study in the
sequence. The first (`odd/research/dj-mixing-techniques.md`, the community study) covered *practitioner* techniques
T1–T11; this study covers the *academic* literature and then explicitly cross-references T1–T11.

Scope: metadata-driven DJ playlist/sequencing engines — automatic mixing and transition generation, playlist
continuation and sequencing, harmonic mixing and key detection, energy/arousal over a sequence, vocal and
instrumental detection plus source separation, danceability/groove features, and set programming as an
optimization problem.

---

## 1. Method, routes, and what failed

Tooling actually used:

- `agent-reach doctor --json`. Reported **ok**: `web` (Jina Reader), `github`, `twitter`, `youtube`, `bilibili`,
  `v2ex`, `rss`, `xiaoyuzhou`. Reported **unavailable**: `exa_search` (Exa not configured), `linkedin` (off),
  `reddit`/`facebook`/`instagram`/`xiaohongshu` (OpenCLI without the Chrome extension), `xueqiu` (login). This study
  is about papers, so it did not need the social backends; the `web` backend (Jina Reader) and public science APIs
  were sufficient.
- **arXiv API** — `http://export.arxiv.org/api/query` returns `301` to HTTPS; all queries were made against
  `https://export.arxiv.org/api/query`. Worked reliably for search and for `id_list` abstract retrieval.
- **Crossref REST** — `https://api.crossref.org/works` and `/works/{DOI}` with a `mailto`. Worked reliably for
  identifiers, venues, years, authors, and (when available) abstracts.
- **Semantic Scholar Graph API** — `https://api.semanticscholar.org/graph/v1/paper/search` returned
  `HTTP 429 Too Many Requests` on every attempt across the session (unauthenticated limit). The single-paper
  endpoint `/paper/DOI:{doi}?fields=...` succeeded intermittently after pauses and was used to recover abstracts
  for three paywalled items. Recorded here because it is a partial route, not a reliable one.
- **Jina Reader** (`https://r.jina.ai/<url>`) for full-text and abstract pages, and DuckDuckGo's HTML endpoint
  through Jina for discovery when no API covered a topic.

Pages that fought back and how each was resolved:

- `dl.acm.org`, `sciencedirect.com`, `online.ucpress.edu` (Music Perception), and some IEEE Xplore pages returned
  CAPTCHA/anti-bot or `404` through Jina. Their abstracts were recovered from Crossref (`abstract` field) or the
  Semantic Scholar DOI endpoint.
- `mediatum.ub.tum.de` returned `429` for one PDF; the identical abstract was read from the DAFx paper archive
  instead.
- Open-access or author-hosted copies were used wherever available (PLOS, PeerJ, Dancecult, DAFx archive, Springer
  chapter abstract, Tilburg University repository, ISMIR `archives.ismir.net`, arXiv, ACM OpenTOC metadata).

**Every paper listed below was fetched.** For each, title, year, venue, and identifier were verified against the
API or the publisher/repository page, and the summary is drawn from the abstract or the retrieved full text. No
citation below is reconstructed from memory. Where a venue could not be verified from the retrieved page, the entry
says so and cites the arXiv identifier instead.

---

## 2. Papers, by research area

Each entry gives: citation; what it demonstrates; data and methods scale; **what XfinAudio could adopt** (named
engine surface); and a confidence note (peer-reviewed vs preprint, reproduced vs single study).

### a. Automatic DJ mixing and transition generation

#### a.1 Zehren, Alunno, Bientinesi (2020) — Automatic Detection of Cue Points for DJ Mixing
**Citation.** M. Zehren, M. Alunno, P. Bientinesi, "Automatic Detection of Cue Points for DJ Mixing,"
arXiv:2007.08411 (2020); published ISMIR 2020 version titled "Automatic Detection of Cue Points for the Emulation
of DJ Mixing."
**Demonstrates.** "Switch points" — the cue points where a transition can be built — can be detected
automatically from EDM audio using general rules distilled from interviews with professional DJs, implemented as
feature extraction plus novelty analysis. About **96%** of the generated points were judged good enough for a DJ
mix, against a manually annotated dataset the authors curated.
**Scale.** Methods paper with a bespoke small-to-medium annotated dataset (M-DJCUE) in EDM; academic, not
industrial.
**Adopt.** A new precomputation of per-track *mix-in / mix-out switch points*, consumed by
`src/xfinaudio/recommendation/optimizer.py` (transition feasibility) and surfaced in explanations next to the
existing per-track `energy_in/out/peak`. Today XfinAudio reasons about transitions from metadata deltas only; this
is the missing audio-side anchor.
**Confidence.** Peer-reviewed (ISMIR 2020) with a released dataset and code; single study, not independently
reproduced. The 96% figure is the authors' own evaluation.

#### a.2 Kim, Choi, Sacks, Yang, Nam (2020) — A Computational Analysis of Real-World DJ Mixes
**Citation.** T. Kim, M. Choi, E. Sacks, Y.-H. Yang, J. Nam, "A Computational Analysis of Real-World DJ Mixes
using Mix-To-Track Subsequence Alignment," ISMIR 2020 (`archives.ismir.net/ismir2020/paper/000352.pdf`);
arXiv:2008.10267.
**Demonstrates.** By aligning a mix to its source tracks with a tempo/key-insensitive subsequence alignment, the
paper recovers cue points, transition length, mix segmentation, and where key/tempo change during a performance.
It reports a wide range of *real-world* transition statistics, i.e. it quantifies how professional DJs actually
join tracks.
**Scale.** The largest DJ-mix corpus in this review: **1,557 mixes, 13,728 tracks, 20,765 transitions** from
1001Tracklists. Industrial-scale corpus; academic methods.
**Adopt.** Direct calibration data for the set-construction inputs: real transition lengths and dwell times feed the
runtime-budget work (community T3) and the default `arc_length` / dwell-time variance in `optimizer.py`; the
alignment method is the reference implementation for a future cue-point precomputation (see a.1).
**Confidence.** Peer-reviewed (ISMIR 2020); corpus-scale and data-driven, but a single study and a single corpus.

#### a.3 Chen, Hsu, Liao, Martínez Ramírez, Mitsufuji, Yang (2021) — Automatic DJ Transitions with Differentiable Audio Effects and GANs
**Citation.** B.-Y. Chen, W.-H. Hsu, W.-H. Liao, M. A. Martínez Ramírez, Y. Mitsufuji, Y.-H. Yang, "Automatic DJ
Transitions with Differentiable Audio Effects and Generative Adversarial Networks," arXiv:2110.06525 (2021).
**Demonstrates.** A GAN whose generator uses two *differentiable DSP* components (an EQ and a fader) learns to set
EQ/fader parameters so a two-track transition resembles real human DJ mixes; a listening test shows competitive
results against several baselines. It formalizes a DJ transition as a small, learnable parameter set.
**Scale.** Data-driven model trained on real DJ mixes; academic prototype with a listening test, not a deployed
product.
**Adopt.** Not a playlist-layer feature. It is evidence that the *transition itself* is parameterizable by EQ/fader
— useful as the long-horizon design for a `mixability` axis, and as caution that pair "compatibility" and pair
"mixability" are different objects (XfinAudio already separates `COMPATIBILITY_COMPONENTS` and
`MIXABILITY_COMPONENTS` in `scoring.py`).
**Confidence.** Preprint on arXiv (work with an ICASSP-track team); peer-review status not verified from the
retrieved page. Single study with a listening test.

#### a.4 Davies, Hamel, Yoshii, Goto (2014) — AutoMashUpper
**Citation.** M. E. P. Davies, P. Hamel, K. Yoshii, M. Goto, "AutoMashUpper: Automatic Creation of Multi-Song
Music Mashups," *IEEE/ACM Transactions on Audio, Speech, and Language Processing* 22(12), 2014.
DOI:10.1109/TASLP.2014.2347135.
**Demonstrates.** Defines a **"mashability"** measure between phrase sections as a combination of *harmonic*
similarity, *rhythmic* similarity, and a *spectral balance* term — and, crucially, evaluates compatibility *after*
allowing key transposition and tempo modification, rather than on unaltered properties. A listening test examined
the relationship between estimated mashability and user enjoyment.
**Scale.** Peer-reviewed methods + listening test on a music collection; not a large-scale study.
**Adopt.** A concrete template for a strengthened compatibility term in
`src/xfinaudio/recommendation/scoring.py`: (i) score harmonic fitness with a key-shift search (the module already
has `KeyShiftConfig` and `_shifted_key`), (ii) add rhythmic/spectral balance as an explicit component (the
`spectral` and `spectral_edge` components and `_spectral_color_penalty` are the current analogues). This is a
*change of objective* — "compatible after a plausible transform" — not a new metadata field.
**Confidence.** Peer-reviewed journal (TASLP); single study, listening test with a modest participant pool.

#### a.5 Delabaere et al. (2025) — AutoMashup
**Citation.** M. Delabaere, L. Miqueu, M. Moreno, G. Bigois, H. Duong, E. Fernandez, F. Manent,
M. Salgado-Herrera, B. Pasdeloup, N. Farrugia, A. Marmoret, "AutoMashup: Automatic Music Mashups Creation,"
arXiv:2508.06516 (2025).
**Demonstrates.** A modern mashup pipeline built on source separation, music analysis, and compatibility
estimation. Two findings matter here: mashup compatibility is **asymmetric** (it depends on which track is
assigned the vocal role and which the accompaniment role), and general-purpose pretrained embeddings (CLAP, MERT)
**fail to reproduce** the perceptual coherence measured by their COCOLA reference.
**Scale.** Academic system study with a reference metric and multiple embeddings; single study.
**Adopt.** (1) The asymmetry result argues for a *directional* transition score and for role-aware handling of the
vocal element — the same element that community technique T2 is about. (2) The embedding negative result is a
warning: do not adopt generic audio embeddings as a compatibility oracle. For XfinAudio this supports keeping the
deterministic `score_transition` in `scoring.py` rather than swapping in an embedding model.
**Confidence.** Preprint (arXiv 2025); single study; explicitly negative result on embeddings, which is unusually
useful.

#### a.6 Argüello, Lanzendörfer, Wattenhofer (2024) — Cue Point Estimation using Object Detection
**Citation.** G. Argüello, L. A. Lanzendörfer, R. Wattenhofer, "Cue Point Estimation using Object Detection,"
arXiv:2407.06823 (2024).
**Demonstrates.** Recasts cue-point estimation for DJ transitions as a computer-vision object-detection problem,
fine-tuning an object-detection transformer. It reports **21,000 manually annotated cue points** over nearly 5,000
tracks — **35× larger** than the previous cue-point dataset — with high adherence to phrasing, and higher precision
than prior methods without low-level musical analysis.
**Scale.** 21k annotations / ~5k tracks, with code, checkpoints, and dataset released; the largest cue-point
resource located in this review.
**Adopt.** A stronger, larger-data alternative to a.1 for a cue-point precomputation feeding `optimizer.py`. The
"phrasing adherence" property maps directly to the phrase-awareness XfinAudio approximates through
`energy_in/out/peak`.
**Confidence.** Preprint (arXiv 2024); dataset-scale and code released; single study.

### b. Playlist continuation, sequencing, and skip prediction

#### b.1 Zamani, Schedl, Lamere, Chen (2018) — The ACM RecSys Challenge 2018 for Automatic Music Playlist Continuation
**Citation.** H. Zamani, M. Schedl, P. Lamere, C.-W. Chen, "An Analysis of Approaches Taken in the ACM RecSys
Challenge 2018 for Automatic Music Playlist Continuation," arXiv:1810.01520 (2018).
**Demonstrates.** Formalizes playlist continuation as sequential recommendation and reports the field's results on
Spotify's **one million** user-generated playlists. The best team reached an **R-precision of 0.2241** and NDCG
0.3946 in the main track. It also analyzes the winners' approaches and open problems.
**Scale.** Industrial-scale dataset (Spotify Million Playlist Dataset); 113 teams, 1,228 main-track runs; benchmark
saturation study.
**Adopt.** An offline evaluation protocol for the sequencing work in `candidate_pool.py` / `optimizer.py`
(R-precision/NDCG-style scoring against held-out real playlists), and a calibration of expectations: even the best
industrial systems land near 0.22 R-precision, i.e. next-track prediction is intrinsically hard. XfinAudio does not
need to beat that; it needs a *deterministic, explainable* ordering, which is a different objective.
**Confidence.** Peer-reviewed venue framing (RecSys Challenge study); a benchmark analysis, not an algorithm paper,
but the most authoritative scale reference in area b.

#### b.2 Vall, Dorfer, Schedl, Widmer (2018) — Hybrid Playlist Continuation via Playlist–Song Membership
**Citation.** A. Vall, M. Dorfer, M. Schedl, G. Widmer, "A Hybrid Approach to Music Playlist Continuation Based on
Playlist-Song Membership," arXiv:1805.09557 (2018).
**Demonstrates.** Instead of asking "which song does the user like," it asks whether a **playlist–song pair fits**,
represented purely as feature vectors, and decides membership. This matches collaborative filtering in the ideal
case while additionally handling non-profiled playlists and rarely-seen songs.
**Scale.** Two curated playlist datasets; academic.
**Adopt.** Frames the candidate-pool gate in `candidate_pool.py` as a *membership* decision (does this track belong
in this set?) rather than a pure preference ranking — which is what `_track_similarity_key` already approximates.
It also motivates a content-feature fallback for the cold-start case that `metadata_gaps.py` (new, in flight)
addresses.
**Confidence.** Preprint (arXiv 2018); single study on two datasets.

#### b.3 Salganik, Liu, Ma, Kang, Chua (2024) — LARP
**Citation.** R. Salganik, X. Liu, Y. Ma, J. Kang, T.-S. Chua, "LARP: Language Audio Relational Pre-training for
Cold-Start Playlist Continuation," arXiv:2406.14333 (2024).
**Demonstrates.** A three-stage contrastive framework that injects multimodal and relational signals into content
representations to beat frozen pretrained content models for **cold-start** playlist continuation (songs with no
interaction data).
**Scale.** Two public datasets; academic, methodological.
**Adopt.** Cold start is exactly XfinAudio's failure mode when MIK metadata is missing. The takeaway is that
*content representations tuned to the specific setting* beat off-the-shelf ones — supporting content-based
sequencing (`candidate_pool.py`, `scoring.py`) as the primary path and treating collaborative signals as optional
enrichment.
**Confidence.** Preprint (arXiv 2024); single study; code and dataset released.

#### b.4 Quadrana, Cremonesi, Jannach (2018) — Sequence-Aware Recommender Systems
**Citation.** M. Quadrana, P. Cremonesi, D. Jannach, "Sequence-Aware Recommender Systems," *ACM Computing Surveys*
51(4), 2018; arXiv:1802.08452.
**Demonstrates.** A taxonomy and review of recommendation methods that consume sequentially-ordered interaction
logs, arguing that order information yields richer user models and behavioral patterns than matrix-completion
formulations, plus open benchmarking challenges.
**Scale.** Survey / framework paper (not an experiment).
**Adopt.** The conceptual license for treating the set as a *sequence objective* rather than a set of good pairs —
which is precisely what `energy_arc.py` and the arc term in `optimizer.py` already implement. Useful as the
citation-level justification for the arc and for a future transition-level objective.
**Confidence.** Peer-reviewed journal survey (CSUR); a review, so no primary effect size of its own.

#### b.5 Brost, Mehrotra, Jehan (2019) — The Music Streaming Sessions Dataset
**Citation.** B. Brost, R. Mehrotra, T. Jehan, "The Music Streaming Sessions Dataset," *The World Wide Web
Conference (WWW) 2019*, DOI:10.1145/3308558.3313641; arXiv:1901.09851.
**Demonstrates.** Releases **160 million listening sessions** with user actions plus audio features and metadata
for ~**3.7 million** unique tracks, including a subset collected under uniformly random recommendation for
counterfactual evaluation. It analyzes user listening/interaction behavior and defines research problems around
session modeling.
**Scale.** The largest-scale resource in this review; industrial corpus released publicly.
**Adopt.** A ground-truth substrate for evaluating any session-level or novelty policy (T6 rotation, T5 reserve):
the session logs let one measure skip behavior as a function of position and repetition. Near-term, it sanctions
using *skip risk* as a soft, position-aware penalty in `scoring.py`/`candidate_pool.py`, but only after an
evaluation spike.
**Confidence.** Peer-reviewed (WWW 2019); a dataset + analysis paper.

#### b.6 Ferraro, Bogdanov, Serra (2019) — Skip Prediction with Boosting Trees on Acoustic Features
**Citation.** A. Ferraro, D. Bogdanov, X. Serra, "Skip prediction using boosting trees based on acoustic features
of tracks in sessions," arXiv:1903.11833 (2019).
**Demonstrates.** Combines boosting-tree models over session and track acoustic features to predict whether a track
in a session will be skipped. It reports a **mean accuracy (MAA) of 0.554**, ranking **14th of 600+** submissions
in the Spotify Sequential Skip Prediction Challenge.
**Scale.** Challenge-scale (hundreds of teams); acoustic features carry real but partial predictive signal.
**Adopt.** Evidence that acoustic features (the same family XfinAudio already computes — loudness, spectral,
danceability) partially predict disengagement, i.e. a "skip-risk" soft signal is defensible. Best used as a
*diversity/novelty* nudge in `candidate_pool.py`, not as a hard gate. The modest 0.554 advises humility about any
single predictive feature.
**Confidence.** Peer-reviewed-community challenge work (WSDM Cup 2019 / arXiv); single study.

### c. Harmonic mixing and key compatibility — is Camelot validated?

This is the most contested area, so it gets a dedicated framing. Four sources matter, and together they form a
clear verdict: **harmonic compatibility matters perceptually, but the specific Camelot grid is neither validated
nor refuted as a model, and the key tags it depends on are demonstrably noisy.**

#### c.1 Gebhardt, Davies, Seeber (2015) — Harmonic Mixing Based on Roughness and Pitch Commonality
**Citation.** R. Gebhardt, M. Davies, B. Seeber, "Harmonic Mixing Based on Roughness and Pitch Commonality,"
*Proc. 18th International Conference on Digital Audio Effects (DAFx-15)*, Trondheim, 2015.
**Demonstrates.** Explicitly contrasts its approach with "existing commercial DJ-mixing software which determine
compatible matches between songs via key estimation and harmonic relationships in the **circle of fifths**." Their
alternative measures **musical consonance at the signal level** (roughness + pitch commonality over sixteenth-note
frames, with a ±6-semitone pitch-shift search for the consonance-maximizing alignment). A **listening test** found
that the most consonant alignments generated by their method were **preferred** to those suggested by an existing
commercial DJ-mixing system.
**Scale.** Psychoacoustic model + listening test; academic, single study, but the only *direct perceptual comparison*
located between a signal-level harmonic model and a commercial circle-of-fifths system.
**Adopt.** Two concrete uses in `src/xfinaudio/recommendation/scoring.py`: (1) treat the harmonic component as a
*consonance estimate with a key-shift search* rather than a discrete Camelot-neighbourhood lookup; (2) treat the
`KeyShiftConfig` as a first-class, scored transform (already partially present) rather than an edge case. This is a
strengthening of `_score_*`-style harmonic scoring, not a new field.
**Confidence.** Peer-reviewed conference (DAFx); **single study**, but the design directly targets the Camelot
premise. This is the strongest single challenge to a strict Camelot grid in the retrieved corpus.

#### c.2 Bibbó Frau & Faraldo (2022) — A New Compatibility Measure for Harmonic EDM Mixing
**Citation.** Bibbó Frau, Faraldo, "A New Compatibility Measure for Harmonic EDM Mixing," in *Lecture Notes in
Computer Science*, Springer, 2022. DOI:10.1007/978-3-031-09917-5_37.
**Demonstrates.** Uses emerging tonal representations (**Tonal Interval Vectors**) to estimate harmonic
compatibility (HC) between recordings specifically for modern dance music and the DJ workflow, producing a
per-candidate HC percentage **and a pitch-transposition interval** that maximizes HC. Tested with *musically
experienced users*, the system's pitch-shift suggestions **improved mixes in 73.7% of cases**.
**Scale.** A software package (with a live-performance GUI) evaluated by music-experienced users; small-sample
human study.
**Adopt.** The most directly deployable finding for `scoring.py`: a richer, continuous harmonic-compatibility score
plus an explicit best-shift recommendation, both of which map onto the existing `harmonic` component and
`KeyShiftConfig`. This can *replace or re-weight* the discrete Camelot-neighbourhood bonus without discarding the
wheel as a UI/explanation layer.
**Confidence.** Peer-reviewed (Springer LNCS); single study, and the 73.7% figure is user-judged improvement, not a
controlled listener experiment.

#### c.3 Korzeniowski & Widmer (2018) — Genre-Agnostic Key Classification with CNNs
**Citation.** F. Korzeniowski, G. Widmer, "Genre-Agnostic Key Classification With Convolutional Neural Networks,"
19th International Society for Music Information Retrieval Conference (**ISMIR 2018**); arXiv:1808.05340.
**Demonstrates.** Modifies a CNN key classifier so that a single **genre-independent** model outperforms
style-specific models across three datasets and generalizes to unseen datasets, beating the state of the art. It
further shows that classifying the *local* key of short excerpts requires the **harmonic coherence of the whole
piece** — short-window key estimates are unreliable.
**Scale.** Three datasets plus unseen-dataset evaluation; academic benchmark, ISMIR main track.
**Adopt.** Directly informs the reliability of the `camelot_key` field that gates XfinAudio's pool. Two uses: (a) a
`quality`/`metadata_gaps`-style caveat that per-track key is an estimate and local keys especially so; (b) if an
in-house key detector is ever added, this is the reference architecture. It is the key evidence for treating the
Camelot tag as *noisy input*, not ground truth.
**Confidence.** Peer-reviewed (ISMIR 2018); single study but a benchmark comparison with state-of-the-art baselines.

#### c.4 Weiß & Schaab (2015) — On the Impact of Key Detection Performance
**Citation.** C. Weiß, M. Schaab, "On the Impact of Key Detection Performance for Identifying Classical Music
Styles," 16th International Society for Music Information Retrieval Conference (**ISMIR 2015**);
`archives.ismir.net/ismir2015/paper/000044.pdf`.
**Demonstrates.** Presents and compares **four automatic key-detection systems** on classical datasets and shows
that downstream tasks (style classification on key-relative chroma) improve **when an efficient key detector is
used** — i.e. key-detection error propagates measurably into anything built on top of the key.
**Scale.** Two datasets (key-detection and style-classification); academic.
**Adopt.** Justifies an explicit *key-confidence / key-error* concept in XfinAudio's readiness or quality layer:
because key error propagates, the engine should distinguish "harmonically compatible per tags" from "harmonically
compatible per reliable tags." This is a `quality/dj_readiness.py`-style warning, not a `scoring.py` weight.
**Confidence.** Peer-reviewed conference (ISMIR 2015); single study.

#### c.5 Eerola & Schutz (2025) — Major-minorness in Tonal Music
**Citation.** T. Eerola, M. Schutz, "Major-minorness in tonal music: Evaluation of relative mode estimation using
expert ratings and audio-based key-finding principles," *Psychology of Music*, 2025.
DOI:10.1177/03057356251326065.
**Demonstrates.** Argues that mode is better modeled on a **continuum** ("relative mode") than as a categorical
major/minor label, and shows an audio-only model predicts relative mode to a degree **closely aligning with expert
annotators** (using both audio and scores) on Bach/Chopin/Shostakovich preludes.
**Scale.** Expert-annotated classical corpus; peer-reviewed, single study.
**Adopt.** A direct critique of the *discretization* behind Camelot (12 keys × {major, minor}). It supports a
"model confidence / mode ambiguity" note in the quality layer for tracks whose mode sits near the boundary — tracks
on which Camelot-based compatibility is least trustworthy.
**Confidence.** Peer-reviewed journal (Psychology of Music); single study, and the corpus is Western classical, so
generalization to EDM is untested by this paper.

**Net verdict for area c:** no located paper *validates the Camelot wheel as a perceptual model*; one (c.1)
empirically favors a signal-level consonance model over a commercial circle-of-fifths system in a listening test;
one (c.2) supports harmonic compatibility mattering but proposes a richer continuous measure; two (c.3, c.4) show
key tags are noisy and that error propagates; one (c.5) shows the major/minor discretization is itself a
simplification. Conclusion: keep harmonic scoring, treat the tag as a noisy proxy, and prefer scored-with-shift
compatibility over a hard wheel lookup.

### d. Energy, arousal, and the shape of a set

#### d.1 Solberg (2014) — "Waiting for the Bass to Drop"
**Citation.** R. T. Solberg, "'Waiting for the Bass to Drop': Correlations Between Intense Emotional Experiences
and Production Techniques in Build-up and Drop Sections of Electronic Dance Music," *Dancecult: Journal of
Electronic Dance Music Culture* 6(1), 61–82, 2014. DOI:10.12801/1947-5403.2014.06.01.04.
**Demonstrates.** A descriptive/interpretive music analysis (spectrograms + a schematic model) of how EDM
production techniques — uplifters, the drum-roll effect, large frequency changes, removal and reintroduction of
bass and kick, and a contrasting **breakdown** — create tension and anticipation correlated with intense emotional
experience. It connects these to Peak Experience / Strong Experiences with Music, explicitly in the club context.
**Scale.** Two tracks, qualitative analysis grounded in music-expectancy theory; small-N by design.
**Adopt.** Mechanistic support for the interior-valley and tension/release structure (community T10): a breakdown
followed by a drop is a *perceptible* tension mechanism, not just an energy dip. This justifies extending
`energy_arc.py` from a single-peak shape toward interior waves, and a "breakdown-heavy" windowed constraint in
`optimizer.py`.
**Confidence.** Peer-reviewed journal article (Dancecult); qualitative, two-track study → supports a *mechanism*,
not an effect size.

#### d.2 Vidas, Nitschinsk, Osborne, Rickard (2026) — Validating Spotify's Energy, Valence, and Danceability
**Citation.** D. Vidas, L. Nitschinsk, M. S. Osborne, N. S. Rickard, "Validating Spotify's 'Valence,' 'Energy,'
and 'Danceability' Audio Features for Music Psychology Research," *Music Perception: An Interdisciplinary
Journal*, 2026. DOI:10.1525/mp.2026.2463161.
**Demonstrates.** N = 244 participants rated 40 excerpts (~20–30 s) on mood, **energy (arousal)**, **danceability**,
familiarity, and enjoyment. Spotify's **energy** was positively associated with human energy ratings (**strong**),
valence moderately, but Spotify's **danceability was not strongly associated with human ratings of danceability**.
**Scale.** N = 244, 40 excerpts — the largest human-perception validation in this review.
**Adopt.** Two engine consequences. (1) The energy axis (`TrackRecord.energy_level`, arc term) is the
*validated* perceptual axis — worth trusting. (2) The **danceability component deserves demotion/uncertainty**:
`ScoringWeights.danceability` defaults to 0.0 today, which this finding supports keeping near zero unless a better
danceability estimator is adopted (see f.2). If `danceability_profile` is displayed, it should be labelled a
*computational proxy*, per this evidence.
**Confidence.** Peer-reviewed journal (Music Perception); single study but well-powered and directly targeted.

#### d.3 Nikrang, Sears, Widmer (2017) — Automatic Estimation of Harmonic Tension
**Citation.** A. Nikrang, D. R. W. Sears, G. Widmer, "Automatic estimation of harmonic tension by distributed
representation of chords," arXiv:1707.00972 (2017).
**Demonstrates.** Trains a word2vec-style model over chord sequences to learn harmonic expectedness and derives a
quantitative *harmonic tension* measure. Statistical comparison of its outputs against empirical music-psychology
results shows the model's predictions **conform very well with human listeners' evidence**.
**Scale.** Model + comparison to human empirical studies; academic.
**Adopt.** A candidate *harmonically-derived tension* signal that could sit alongside the perceived-energy arc,
especially for tracks where `energy_level` is coarse. Long-term it could condition `energy_arc.py`'s target shape;
near-term it is evidence that "tension" is computable from harmony and not only from loudness.
**Confidence.** Preprint (arXiv 2017); conforms to prior human studies rather than running a new listener test.

#### d.4 Abel & Goddard (2024) — The Art of Concert Setlist Composition
**Citation.** E. Abel, A. Goddard, "The Art of Concert Setlist Composition — A Data Driven Analysis of Bruce
Springsteen's Setlist Curation Over His Career," OSF preprint, 2024. DOI:10.31235/osf.io/869mn.
(A related peer-reviewed article by the same authors on setlist preferences appears in the 2023 IEEE IIAI-AAI
Winter Congress, DOI:10.1109/iiai-aai-winter61682.2023.00067.)
**Demonstrates.** Analyzes Springsteen's setlists across his career to characterize how he balances **conflicting
constraints** — promoting the newest album versus drawing on a huge back-catalogue — while keeping setlists
coherent as a whole. It treats setlist composition as a multi-objective curation problem rather than a
like-list.
**Scale.** A career-scale corpus ("thousands of live shows"); preprint, single-artist case study.
**Adopt.** Concrete support for community technique T4 (slot-role/context programming): the paper shows that real
programming is a multi-objective trade-off under context, which is exactly a `Pauws`-style penalty-function
formulation (g.1) applied to set ordering. Near-term it argues for making the trade-off explicit (weighted terms in
`strategies.py` / `optimizer.py`) rather than implicit.
**Confidence.** Preprint (OSF); single-artist case study → supports the *structure* of the problem, not a general
law.

#### d.5 van den Bosch, Salimpoor, Zatorre (2013) — Familiarity Mediates Arousal and Pleasure
**Citation.** I. van den Bosch, V. N. Salimpoor, R. J. Zatorre, "Familiarity mediates the relationship between
emotional arousal and pleasure during music listening," *Frontiers in Human Neuroscience* 7:534, 2013.
DOI:10.3389/fnhum.2013.00534.
**Demonstrates.** Two experiments show that the strong arousal–pleasure relationship observed with **familiar**
music is mediated by familiarity: with entirely unfamiliar music the link is weaker, and experimentally
establishing familiarity by repetition restores it. Memory/expectation over time is a major factor in musical
pleasure.
**Scale.** Two behavioral experiments (psychophysiology, EDA); peer-reviewed, single research group.
**Adopt.** The strongest scientific support for community technique T5 (floorfiller/familiarity reserve): a rising
familiarity target over the set is psychologically grounded, and the existing inert-by-default `FamiliaritySignal`
in `recommendation/familiarity.py` is the ready substrate. Implement as a *position-increasing target* in the
`energy_arc.py` style rather than a flat preference.
**Confidence.** Peer-reviewed journal (Frontiers); single group; supports a mechanism (familiarity → pleasure),
tested with repeated exposure, not with DJ-set programming.

### e. Vocal/instrumental detection and source separation (the evidence behind T2)

#### e.1 Lee, Choi, Nam (2018) — Revisiting Singing Voice Detection
**Citation.** K. Lee, K. Choi, J. Nam, "Revisiting Singing Voice Detection: a Quantitative Review and the Future
Outlook," arXiv:1806.01180 (2018).
**Demonstrates.** Performs an **error analysis** on three recent singing-voice-detection (SVD) systems and shows
that their apparently high performance hides pitfalls that the standard datasets do not expose; it proposes more
robust evaluation directions. The message is that SVD is *solvable but not solved*.
**Scale.** Quantitative review + internally curated/generated test sets; academic.
**Adopt.** Directly relevant to implementing community technique T2 (vocal spacing): this is the state-of-the-art
survey of the exact subsystem ("is there a vocal present at time t?") XfinAudio would need. The caution is that
SVD error exists and must degrade gracefully to "unknown."
**Confidence.** Preprint (arXiv 2018); a review/error-analysis, not a new listener study.

#### e.2 Fourer & Peeters (2018) — Single-Channel BASS for Singing Voice Detection
**Citation.** D. Fourer, G. Peeters, "Single-Channel Blind Source Separation for Singing Voice Detection: A
Comparative Study," arXiv:1805.01201 (2018).
**Demonstrates.** Uses single-channel blind audio source separation as a preprocessing step for **unsupervised**
SVD, unifies three BASS methods in one formalism, compares them on both separation accuracy and detection accuracy,
and benchmarks against supervised methods and CNNs.
**Scale.** Comparative study with numerical simulations and evaluation on standard SVD data; academic.
**Adopt.** An *unsupervised* vocal-activity route matters because XfinAudio has no labeled vocal dataset and cannot
train on the user's library. This is a concrete, precomputable path for a `vocal_activity` signal that a
`scoring.py` adjacency penalty / `optimizer.py` window constraint would consume for T2.
**Confidence.** Preprint (arXiv 2018); single study, comparative.

#### e.3 Sun, Zhang, Yu, Chen, Li (2020) — Singing Voice Separation for SVD in Polyphonic Music
**Citation.** Y. Sun, X. Zhang, Y. Yu, X. Chen, W. Li, "Investigation of Singing Voice Separation for Singing
Voice Detection in Polyphonic Music," arXiv:2004.04040 (2020).
**Demonstrates.** A two-stage SVD pipeline that first separates the singing voice and then applies Long-term
Recurrent Convolutional Networks with median-filter smoothing; it **outperforms the state of the art** on two
public datasets (Jamendo Corpus, RWC pop).
**Scale.** Two public benchmarks; academic.
**Adopt.** The two-stage "separate then detect" pattern is the recommended architecture if XfinAudio ever computes
vocal activity in-house; it is the strongest accuracy signal for the feasibility half of T2.
**Confidence.** Preprint (arXiv 2020); single study.

#### e.4 Défossez (2021) — Hybrid Spectrogram and Waveform Source Separation (Demucs)
**Citation.** A. Défossez, "Hybrid Spectrogram and Waveform Source Separation," arXiv:2111.03600 (2021).
**Demonstrates.** An end-to-end hybrid model lets the network decide spectrogram vs waveform domain per source;
the hybrid Demucs architecture **won the Music Demixing Challenge 2021** (Sony), with additions such as compressed
residual branches and local attention.
**Scale.** Competition-winning system on a public music-demixing benchmark; code released.
**Adopt.** Practical vocal-stem extraction for building a vocal-activity precomputation (T2) without a bespoke
model. Caveat: MDX-style separation is compute-heavy — this is a *batch precomputation*, never a runtime step, and
it belongs behind the same optional/inert default gate as the other audio analyses.
**Confidence.** Preprint (arXiv 2021) with an independent competition result; widely reproduced.

### f. Danceability, groove, and beat-perceptual features

#### f.1 Senn, Kilchenmann, Bechtold, Hoesl (2018) — Groove in Drum Patterns
**Citation.** O. Senn, L. Kilchenmann, T. Bechtold, F. Hoesl, "Groove in drum patterns as a function of both
rhythmic properties and listeners' attitudes," *PLOS ONE* 13(6):e0199604, 2018.
DOI:10.1371/journal.pone.0199604.
**Demonstrates.** Defines groove as the pleasurable urge to move and investigates **248 reconstructed drum
patterns** across pop, rock, funk, heavy metal, rock'n'roll, hip hop, soul, and R&B, finding that **syncopation,
event density, beat salience, and rhythmic variability** are positively associated with groove — modulated by
listeners' attitudes.
**Scale.** 248 stimuli across eight styles, listener ratings; peer-reviewed, the largest groove study here.
**Adopt.** Concrete feature directions for the *density* half of community technique T8 ("denser arrangement =
more energy"): event density and rhythmic variability are audio-computable proxies for perceptual intensity that
do not depend on BPM. They would live next to `audio/danceability.py` and `audio/spectral_profile.py` as a groove
signal that `scoring.py` could expose.
**Confidence.** Peer-reviewed (PLOS ONE); single study, stimuli are synthesized drum patterns rather than full
tracks.

#### f.2 Wu (2025) — Predicting Danceability and Song Ratings
**Citation.** W. Wu, "Predicting danceability and song ratings using deep learning and auditory features," *PeerJ
Computer Science* 2025. DOI:10.7717/peerj-cs.3009.
**Demonstrates.** A deep framework jointly estimates **danceability** and popularity by fusing a BiLSTM over
categorical inputs with a ResNet over numerical auditory features via cross-attention; it consistently outperforms
both classical ML baselines and recent deep models.
**Scale.** A single study on a song-metadata/feature corpus; peer-reviewed (light review).
**Adopt.** A candidate replacement for XfinAudio's `danceability_profile` if the current estimator proves weak
(see d.2). It reinforces that danceability is learnable from auditory features — but as a *model output*, not
ground truth, so it should feed the engine only with an explicit confidence/`metadata_status`-style caveat.
**Confidence.** Peer-reviewed (PeerJ CS); single study; not independently reproduced.

#### f.3 Vidas et al. (2026)
Cross-listed with d.2: the danceability non-validation finding is the single most important constraint on any
danceability-weighted engine surface.

### g. Set programming as an optimization problem

#### g.1 Pauws, Verhaegh, Vossen (2008) — Music Playlist Generation by Adapted Simulated Annealing
**Citation.** S. Pauws, W. Verhaegh, M. Vossen, "Music playlist generation by adapted simulated annealing,"
*Information Sciences* 178(3), 2008. DOI:10.1016/j.ins.2007.08.019.
**Demonstrates.** Introduces a formal model for automatic playlist generation, **proves it NP-hard**, and solves it
with a local-search/simulated-annealing procedure: a penalty-function formulation, a neighborhood structure, and
three heuristics (song-domain reduction, partial constraint voting, two-level neighborhood). It compares against a
constraint-satisfaction baseline on both penalty and **subjective user evaluation**, with a "dramatic improvement."
**Scale.** Algorithm + user evaluation; the canonical peer-reviewed optimization reference for playlist ordering.
**Adopt.** This is the theoretical backbone for `src/xfinaudio/recommendation/optimizer.py`. The penalty-function
framing maps cleanly onto XfinAudio's constraints (BPM adjacency, duplicate groups, arc adherence, T1/T3/T4/T10
constraints): each becomes a penalty term, and the arc bonus is one term among many. It also validates local
search (XfinAudio's beam/exact approach) as the right algorithmic family for this NP-hard problem.
**Confidence.** Peer-reviewed journal (Information Sciences); single study, but a foundational and widely cited
formulation.

#### g.2 Furini & D'Arcangelo (2021) — Automatic and User-Tailored Playlist Sequencing
**Citation.** M. Furini, S. D'Arcangelo, "Automatic and User-Tailored Playlist Sequencing," *Proc. Conference on
Information Technology for Social Good (GoodIT) 2021*. DOI:10.1145/3462203.3475893.
**Demonstrates.** Argues that playlist research has over-focused on *which songs* and neglected the **sequencing**
process; proposes learning a user's sequencing criterion from their listening history and evaluates with real
users, finding **personalization important** for sequencing quality.
**Scale.** Early-stage method with a real-user evaluation; academic, small.
**Adopt.** Supports the `strategies.py` direction (per-persona/per-gig weight presets) and argues for a
*user-preference* sequencing term in `optimizer.py`/`candidate_pool.py`. It is the sequencing-specific counterpart
to g.1's generic optimization framing.
**Confidence.** Peer-reviewed (GoodIT 2021); small, early-stage, self-described as preliminary.

---

## 3. Cross-reference to the community study (T1–T11) — SUPPORTS / CONTRADICTS / SILENT

This is the section the engine work should act on. For each community technique from
`odd/research/dj-mixing-techniques.md`, the scientific corpus is classified. The scientific literature is younger
and thinner than the practitioner consensus, and it frequently *supports the mechanism while remaining silent on
the specific claim* — that distinction is stated explicitly.

| ID | Community technique | Verdict | Key scientific evidence |
|---|---|---|---|
| T1 | Triads / pre-rehearsed clusters | **SILENT** (mechanism supported) | No study tests rehearsed clusters. Kim 2020 (a.2) and Zehren 2020 (a.1) show transitions are structured and analyzable; Pauws 2008 (g.1) provides the cluster-as-penalty-term machinery. |
| T2 | Vocal spacing (don't cluster vocals) | **SUPPORTS feasibility; SILENT on perception** | SVD/SVS literature (e.1–e.3) plus Demucs (e.4) make a vocal-activity signal computable; AutoMashup (a.5) shows the vocal/accompaniment *role* changes compatibility. No paper measures vocal spacing against listener response. |
| T3 | Runtime budgeting | **SILENT** | No study on runtime budgeting. Kim 2020 (a.2) reports real dwell/transition lengths that can calibrate it; Pauws 2008 (g.1) supports adding a duration penalty term. |
| T4 | Slot-role / venue profile | **SUPPORTS (partially); SILENT on venue timing** | Solberg 2014 (d.1) and Abel & Goddard 2024 (d.4) show programming is context- and role-dependent; no study tests arrival/peak/exit times. |
| T5 | Floorfiller reserve / rising familiarity | **SUPPORTS (mechanism)** | van den Bosch 2013 (d.5): familiarity mediates arousal→pleasure. Brost 2019 (b.5) and Ferraro 2019 (b.6) show familiarity/repetition relate to skip behavior. No study tests anthem reservation specifically. |
| T6 | Rotation / cross-DJ overlap | **SILENT on cross-DJ overlap; SUPPORTS novelty modeling** | Skip/session literature (b.5, b.6) supports modeling repetition and skip risk; no study on overlapping with a previous DJ's set. |
| T7 | Genre bridges / stacked sections | **SUPPORTS (partially); SILENT on bridge tagging** | AutoMashUpper (a.4) formalizes cross-track fits via key/tempo transform; AutoMashup (a.5) shows compatibility is directional; LARP (b.3) supports cohesive extension. No bridge-track tagging study. |
| T8 | Multi-tempo anchor lanes (energy ≠ BPM) | **SUPPORTS** | Vidas 2026 (d.2) validates energy as a perceptual axis distinct from tempo; Solberg 2014 (d.1) ties intensity to production technique, not BPM; Senn 2018 (f.1) ties groove to syncopation/density. |
| T9 | Contingency branches | **SILENT** | No study on alternate pre-validated continuations. Pauws 2008 (g.1) and Furini 2021 (g.2) support generating alternate sequencings as an optimization/search artifact. |
| T10 | Interior valleys / breakdown density | **SUPPORTS mechanism; SILENT on density rule** | Solberg 2014 (d.1): breakdown→drop is a tension/release mechanism; Nikrang 2017 (d.3): harmonic tension is modelable and matches human data. No numeric breakdown-density rule exists. |
| T11 | Harmonic-variety guardrail (weakly sourced) | **SUPPORTS the caution; CONTESTS the Camelot grid** | Gebhardt 2015 (c.1) found a signal-level consonance model preferred over a commercial circle-of-fifths system; Bibbó & Faraldo 2022 (c.2) support harmonic fit via a richer model; Korzeniowski 2018 (c.3), Weiß & Schaab 2015 (c.4), Eerola & Schutz 2025 (c.5) show key/mode tags and discretization are noisy. |

### 3.1 The three explicit questions the task asked

**Does any paper evaluate whether key compatibility matters to listeners?**
Partially, and it is the strongest result in area c. **Gebhardt, Davies & Seeber 2015 (c.1)** ran a **listening
test** and found that the most *consonant* (signal-level) alignments were **preferred to those suggested by an
existing commercial DJ-mixing system** — a system of the kind that uses key estimation and the circle of fifths.
So: listeners do respond to harmonic alignment, *and* the specific circle-of-fifths tag mechanism is not
demonstrably the best predictor of that response. **Bibbó Frau & Faraldo 2022 (c.2)** corroborate that harmonic
compatibility is real and improvable (73.7% of pitch-shift suggestions improved mixes with experienced users).
**No paper** was found that measures whether *Camelot-tag compatibility* specifically improves perceived mix
quality versus an arbitrary labelled key relationship. Verdict: harmonic compatibility matters; the Camelot *grid*
is not validated.

**Does science back "don't cluster vocals" (T2)?**
**No.** The literature supports the *prerequisite*, not the *claim*. Singing-voice detection and separation
(e.1–e.4) demonstrate that a vocal-presence signal is computable at good accuracy, and e.1 warns it is not solved.
**AutoMashup (a.5)** adds a directly relevant nuance: track-pair compatibility is **asymmetric** and depends on
which track takes the vocal role — evidence that "vocals are a distinct role" is real. But **not one located paper
tests whether clustering vocals in a set harms listener experience or engagement.** T2's behavioural claim is
scientifically untested; only its implementation is feasible.

**Is the Camelot wheel validated?**
**No validated model, and meaningful grounds for caution.**
- No peer-reviewed source located validates the Camelot wheel as a perceptual or predictive model (searches
  returned only commercial DJ-tool pages — see §5).
- **c.1** empirically favors a *signal-level consonance* method over a commercial circle-of-fifths system.
- **c.2** shows compatibility is real but better modeled continuously (Tonal Interval Vectors) with pitch-shift
  search.
- **c.3** and **c.4** show the key tag itself is an estimate, that genre-agnostic detection is a genuine research
  problem, and that local-key estimates require whole-piece context and that key-detection error propagates
  downstream.
- **c.5** shows even the major/minor dichotomy is a *continuum* being discretized.
Verdict: the harmonic *intent* is supported; the specific wheel is an unvalidated, noisy proxy. It is reasonable
to keep it as a UI/explanation layer while moving the scoring toward a scored, shift-aware compatibility measure.

---

## 4. Ranked adoptability table

Ranked by expected value relative to effort and evidence maturity. "Effort" is engineering effort to wire the
finding into the engine (not to build new research). "Maturity" is evidence strength: peer-reviewed + reproduced
> peer-reviewed single study > preprint.

| # | Paper / finding | Engine surface | Effort | Expected value | Maturity |
|---|---|---|---|---|---|
| 1 | Pauws 2008 (g.1) — APG is NP-hard; penalty-function + local search | `optimizer.py` (constraint/penalty model); `energy_arc.py` as one term | Low (framing refactor) | High — validates and structures the core optimizer | Peer-reviewed, foundational |
| 2 | Vidas 2026 (d.2) — energy validated, danceability NOT validated | `scoring.py` (`danceability` weight), `audio/danceability.py` caveat | Very low | High — prevents weighting on an invalidated feature | Peer-reviewed, N=244 |
| 3 | Kim 2020 (a.2) — real transition/dwell statistics | `optimizer.py` (`arc_length`, dwell variance), T3 runtime budget | Low–medium | High — grounds runtime budgeting in real data | Peer-reviewed, 1,557 mixes |
| 4 | Gebhardt 2015 (c.1) — signal-level consonance beats circle-of-fifths | `scoring.py` harmonic component | Medium | High — the one direct test of the Camelot premise | Peer-reviewed, single study |
| 5 | Bibbó & Faraldo 2022 (c.2) — TIV compatibility + best shift | `scoring.py` harmonic + `KeyShiftConfig`/`_shifted_key` | Medium | High — richer, continuous harmonic score | Peer-reviewed, single study |
| 6 | van den Bosch 2013 (d.5) — familiarity mediates arousal→pleasure | `recommendation/familiarity.py` policy, `energy_arc.py` target | Low–medium | High for residencies — grounds T5 | Peer-reviewed, single group |
| 7 | Korzeniowski & Widmer 2018 (c.3) — key tags are noisy; local keys need context | `quality/dj_readiness.py`, `metadata_gaps.py` key-confidence | Low | Medium-high — makes key-based gates honest | Peer-reviewed (ISMIR) |
| 8 | Solberg 2014 (d.1) — breakdown→drop tension mechanism | `energy_arc.py` multi-valley, `optimizer.py` breakdown window | Medium | Medium-high — mechanism for T10 | Peer-reviewed, small-N |
| 9 | Senn 2018 (f.1) — groove from syncopation/event density | new precompute next to `audio/danceability.py` | Medium | Medium — audio density proxy for T8/T10 | Peer-reviewed, 248 stimuli |
| 10 | Lee 2018 / Fourer 2018 / Sun 2020 (e.1–e.3) — SVD is feasible and imperfect | new vocal-activity precompute for T2 | Medium–high | Medium — enables T2 without promising its perception claim | Preprint, reviews/comparisons |
| 11 | Brost 2019 (b.5) — 160M-session corpus with skips | offline evaluation harness for `candidate_pool.py` | Medium | Medium — evaluation substrate for novelty/T6 | Peer-reviewed (WWW), dataset |
| 12 | Ferraro 2019 (b.6) — acoustic features partially predict skips (MAA 0.554) | `candidate_pool.py` soft skip-risk nudge | Medium | Medium — evidence for a soft signal | Challenge work, single study |
| 13 | Zamani 2018 (b.1) — APC benchmark saturated at R-precision ≈ 0.22 | offline eval protocol for `optimizer.py` | Medium | Medium — calibrates expectations | Peer-reviewed benchmark analysis |
| 14 | Zehren 2020 / Argüello 2024 (a.1, a.6) — cue-point detection at 96% / 21k-annotation scale | new cue-point precompute feeding `optimizer.py` | High | Medium-high — long-term transition anchoring | Preprints; datasets released |
| 15 | AutoMashUpper 2014 (a.4) — mashability with key/tempo transform | `scoring.py` (harmonic + spectral balance + rhythmic) | Medium | Medium — template, overlaps #4/#5 | Peer-reviewed (TASLP) |
| 16 | AutoMashup 2025 (a.5) — compatibility is asymmetric; embeddings fail | directional `score_transition`; do NOT adopt embeddings | Low (a decision) | Medium — avoids a wrong turn | Preprint, negative result |
| 17 | Défossez 2021 (e.4) — Demucs won MDX 2021 | batch vocal-stem precompute for T2 | High | Medium — heavy compute, batch only | Preprint, competition-validated |
| 18 | Quadrana 2018 (b.4) — sequence-aware recommendation taxonomy | documentation/justification for the arc term | Very low | Low-medium — citation-level framing | Journal survey |
| 19 | Eerola & Schutz 2025 (c.5) — mode is a continuum | `quality/dj_readiness.py` mode-ambiguity note | Low | Low-medium — nuance on key discretization | Peer-reviewed, classical corpus |
| 20 | Nikrang 2017 (d.3) — harmonic tension model matches human data | possible tension term in `energy_arc.py` | High | Low-medium — research-grade | Preprint |
| 21 | Wu 2025 (f.2) — deep danceability estimator | replacement for `audio/danceability.py` | High | Low-medium until d.2 is resolved | Peer-reviewed (light), single study |
| 22 | Abel & Goddard 2024 (d.4) — setlists as multi-objective curation | `strategies.py` explicit trade-offs | Low | Low-medium — motivation, not method | Preprint, single artist |
| 23 | Vall 2018 / LARP 2024 / Furini 2021 (b.2, b.3, g.2) — membership, cold start, personalization | `candidate_pool.py`, `strategies.py` | Medium–high | Low-medium — direction, not near-term code | Preprints / single small study |

---

## 5. Limitations — what this literature does NOT answer

1. **The Camelot wheel is untested.** No peer-reviewed paper located here validates the wheel as a perceptual
   model. A targeted search returned only commercial DJ-tool and tutorial pages (Mixed In Key, DJ.Studio,
   learningtodj, harmonyset, etc.), i.e. vendor/practitioner material, not evidence. The wheel's prevalence is a
   market fact, not a validated one.
2. **No study measures a DJ *set* as an object.** Every "energy/set" paper here studies either a *single track's*
   internal structure (Solberg, Nikrang), *mood perception of excerpts* (Vidas), or *concert setlists as text*
   (Abel & Goddard). None measures the perceived quality of a 60–120-minute DJ set as a function of its ordering.
   The engine's whole-set arc is therefore *extrapolated*, not validated.
3. **Vocal spacing (T2) is behaviourally untested.** Detection feasibility is well supported; the claim that
   clustering vocals hurts the floor is not. The vocal-spacing ratio and the "couple of instrumentals, a vocal"
   pattern have no scientific backing.
4. **Runtime budgeting (T3), triads (T1), contingency branches (T9), and breakdown-density rules (T10) have no
   direct studies.** They are optimization-shaped problems (Pauws) with practitioner-defined objectives, not
   empirically parameterized ones.
5. **Metrics in area b are pessimistic and not directly transferable.** Best-in-class playlist continuation sits
   near R-precision 0.22, and skip prediction near MAA 0.55. These numbers describe *implicit-feedback prediction
   on streaming corpora*, a different problem from *deterministic, explainable DJ-set construction*. They should
   calibrate humility, not define XfinAudio's success metric — no ground-truth "good DJ set" dataset exists in the
   retrieved corpus.
6. **Genre skew.** Key-detection and mode studies here use Western classical and mixed-genre corpora (c.3–c.5);
   groove uses synthesized drum patterns (f.1); Solberg analyzes two EDM tracks. None is a large EDM corpus.
   Evidence transfer to club EDM is an assumption, not a result.
7. **Small-N and single-study domination.** Aside from Vidas (N=244) and the large *datasets* (Brost; RecSys MPD;
   Kim's 1,557 mixes), nearly every perceptual result is a single study with a small participant pool. Almost
   nothing is independently reproduced.
8. **Graphical/audio deep models are not deployable at XfinAudio's layer.** The transformer/GAN/CNN systems
   (a.3, a.6, e.4, f.2) are research prototypes with real compute costs; they are relevant to *precomputation* and
   to the long-term design, not to metadata-driven sequencing in real time.
9. **Retrieval limitations.** Semantic Scholar's search endpoint was unusable (persistent 429); its DOI endpoint
   recovered three abstracts. Several publisher pages (ACM, ScienceDirect, UC Press, parts of IEEE) were blocked
   by anti-bot measures through the available route, so those abstracts were obtained from Crossref or Semantic
   Scholar metadata rather than the publisher's rendered abstract page. Venues were verified via Crossref where a
   DOI existed; some arXiv items could not have their final publication venue verified and are cited by arXiv ID.
10. **No experiment was run.** Everything about "what XfinAudio could adopt" is a design inference from abstracts
    and methods, not a measured improvement on XfinAudio's own library. Each adoptability row implies a spike.

---

## 6. Identifier index (all fetched)

- a.1 Zehren, Alunno, Bientinesi 2020 — arXiv:2007.08411 (ISMIR 2020: "…for the Emulation of DJ Mixing").
- a.2 Kim, Choi, Sacks, Yang, Nam 2020 — ISMIR 2020; arXiv:2008.10267.
- a.3 Chen, Hsu, Liao, Martínez Ramírez, Mitsufuji, Yang 2021 — arXiv:2110.06525.
- a.4 Davies, Hamel, Yoshii, Goto 2014 — DOI:10.1109/TASLP.2014.2347135.
- a.5 Delabaere et al. 2025 — arXiv:2508.06516.
- a.6 Argüello, Lanzendörfer, Wattenhofer 2024 — arXiv:2407.06823.
- b.1 Zamani, Schedl, Lamere, Chen 2018 — arXiv:1810.01520.
- b.2 Vall, Dorfer, Schedl, Widmer 2018 — arXiv:1805.09557.
- b.3 Salganik, Liu, Ma, Kang, Chua 2024 — arXiv:2406.14333.
- b.4 Quadrana, Cremonesi, Jannach 2018 — *ACM Computing Surveys* 51(4); arXiv:1802.08452.
- b.5 Brost, Mehrotra, Jehan 2019 — *WWW 2019*; DOI:10.1145/3308558.3313641; arXiv:1901.09851.
- b.6 Ferraro, Bogdanov, Serra 2019 — arXiv:1903.11833 (Spotify Sequential Skip Prediction Challenge).
- c.1 Gebhardt, Davies, Seeber 2015 — DAFx-15 (no DOI; DAFx paper archive).
- c.2 Bibbó Frau, Faraldo 2022 — Springer LNCS; DOI:10.1007/978-3-031-09917-5_37.
- c.3 Korzeniowski, Widmer 2018 — ISMIR 2018; arXiv:1808.05340.
- c.4 Weiß, Schaab 2015 — ISMIR 2015; `archives.ismir.net/ismir2015/paper/000044.pdf`.
- c.5 Eerola, Schutz 2025 — *Psychology of Music*; DOI:10.1177/03057356251326065.
- d.1 Solberg 2014 — *Dancecult* 6(1); DOI:10.12801/1947-5403.2014.06.01.04.
- d.2 Vidas, Nitschinsk, Osborne, Rickard 2026 — *Music Perception*; DOI:10.1525/mp.2026.2463161.
- d.3 Nikrang, Sears, Widmer 2017 — arXiv:1707.00972.
- d.4 Abel, Goddard 2024 — OSF preprint DOI:10.31235/osf.io/869mn.
- d.5 van den Bosch, Salimpoor, Zatorre 2013 — *Frontiers in Human Neuroscience* 7:534;
  DOI:10.3389/fnhum.2013.00534.
- e.1 Lee, Choi, Nam 2018 — arXiv:1806.01180.
- e.2 Fourer, Peeters 2018 — arXiv:1805.01201.
- e.3 Sun, Zhang, Yu, Chen, Li 2020 — arXiv:2004.04040.
- e.4 Défossez 2021 — arXiv:2111.03600.
- f.1 Senn, Kilchenmann, Bechtold, Hoesl 2018 — *PLOS ONE*; DOI:10.1371/journal.pone.0199604.
- f.2 Wu 2025 — *PeerJ Computer Science*; DOI:10.7717/peerj-cs.3009.
- g.1 Pauws, Verhaegh, Vossen 2008 — *Information Sciences*; DOI:10.1016/j.ins.2007.08.019.
- g.2 Furini, D'Arcangelo 2021 — GoodIT 2021; DOI:10.1145/3462203.3475893.
