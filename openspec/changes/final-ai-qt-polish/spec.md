# Behavior requirements

1. GIVEN a Create screen during construction or teardown, WHEN a layout event or
   deferred reveal arrives, THEN it safely ignores missing/deleted Qt children.
   A visible new confirmation is revealed only after its layout has current geometry.
2. GIVEN a completed optional-AI result, WHEN local filters are applied or edited,
   or an Editor preview is replaced, consumed or dismissed, THEN status is neutral
   and a newly created local preview survives. Explicit in-flight Cancel retains
   its cancellation and already-sent-data notice.
3. GIVEN Live with three candidates, history and AI commentary, WHEN shown at
   1000×700 or 1440×1000, THEN window size is preserved, candidate actions remain
   at least 32 pixels high, all content is reachable, and the optional panel does
   not stretch its labels into large vertical gaps.
