# Observable requirements

- Given an authorized metadata library, when profile completion runs, then original spectral, danceability and edge analyses run in that order without writing source audio or invoking providers/loudness/Serato services.
- Given a current-version cached profile whose source identity still matches, when completion repeats or the app restarts, then that profile is reused without analysis. Changed, unavailable, symlinked or stale-version sources are never reported as current profiles.
- Given cancellation, when an in-flight analysis settles, then no late profile is persisted/published and later stages do not start. Earlier committed profiles survive and retry resumes missing work.
- Given silence, decode errors or unavailable dependencies, when completion returns, then bounded summaries distinguish complete, partial, cancelled and unavailable states without fabricated profiles, private paths or raw exceptions.
- Given successful metadata scan/rescan, when the client receives metadata, then it initiates the cancellable completion job and displays stage/count progress; an explicit retry is available.
- Given existing preferences, when spectral cohesion is read, then the original 0.5 default is visible. A revision-bound finite number in [0,1] is saved immutably, preserving unrelated preferences and invalidating scoring-dependent reviews/Live contexts.
- Given any cohesion setting and completed profiles, when Prep/Live uses original scoring, then the same setting reaches original scoring with all strategy gates/control priorities preserved.
- Given genuine synthetic audible audio, when original-engine completion and both color strategies run, then all three profile classes persist, both strategies yield eligible tracks, and source hashes/timestamps remain unchanged.
