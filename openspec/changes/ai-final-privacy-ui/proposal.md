# Final AI privacy and saved-set safeguards

Fix three bounded final-review findings: relative audio paths reaching AI,
unconfirmed saved-set deletion, and missing Spanish labels on core AI controls.
No new feature, dependency, real provider request, audio write, or publication.

Success: synthetic transport excludes recognized relative audio paths; deleting a
named saved set requires explicit confirmation with Cancel as default; compiled
Spanish catalogs translate the reviewed controls in their real QObject contexts.

Risks: path matching can consume musical text; modal deletion can regress Cancel;
translation context mismatches can silently fall back to English. Regression
coverage must preserve genre/ratio text, denial, and runtime translations.
Rollback each independent conventional-commit slice. Chained review slices stay
under 400 changed lines: privacy, deletion, core-control catalogs, then privacy
disclosure catalogs and compiled assets.
