# Remove Recommendation Presenter Wrapper

Remove the obsolete `xfinaudio.desktop.recommendation_presenter` compatibility wrapper because desktop should not re-export recommendation policy functions.

In scope: delete unused desktop wrapper, preserve candidate-pool tests against the owning recommendation/application modules, add SDD evidence.
Out of scope: changing recommendation behavior, scoring semantics, DSP/audio mutation, export formats, live Serato DB V2 writes.

Success: no source/test import references `xfinaudio.desktop.recommendation_presenter`; focused recommendation tests pass.
