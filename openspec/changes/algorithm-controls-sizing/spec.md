# Observable requirements
1. GIVEN a complete all-120 BPM a,b,c,d pool, start a and end or locked d, WHEN same_energy is capped at two, THEN d survives and end d is terminal.
2. GIVEN more mandatory paths than count, WHEN capped, THEN return no generated playlist and explicit control/count conflict; never silently remove controls.
3. GIVEN a feasible ordered subsequence preserving controls and the 3% gate, WHEN trimming, THEN select it without exceeding count; if none fits, report inability rather than a false proof of global infeasibility.
4. GIVEN Prep target three and requested end f in a six-track compatible pool, THEN every variant ends f and has at most three tracks. Required tracks are mandatory, not disposable after generation.
5. GIVEN six four-minute tracks and nine-minute arc request, THEN return three tracks covering the slot. Mixed durations require checking actual selected duration and extending selection when possible, not trusting the mean.
6. GIVEN insufficient known duration or unknown durations, THEN explicitly report shortage/unknown duration without inventing runtime.
7. GIVEN a manual prefix exceeding the duration estimate, THEN preserve it with existing warning. Manual prefix remains authoritative; conflicting start keeps existing warning precedence.

8. GIVEN sufficient compatible eligible Prep tracks, WHEN count40 is requested or excluded tracks precede eligible records, THEN pool capping cannot silently restrict to25 or spend slots on excluded tracks. Report count shortage explicitly if the result is shorter.
