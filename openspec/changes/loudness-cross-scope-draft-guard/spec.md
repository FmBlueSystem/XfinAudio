# Observable requirements
- All six unsaved scopes disable preview/reanalysis/run, name the actual drafts, and provide navigation to each preserved draft
- Save/Discard remain available; resolving one draft retains every other guard; clean/no-op/reverted state permits preview
- New previews receive keyboard focus and an accessible summary once, with no implicit execution; late results after navigation do not steal focus
- Draft edits/discard immediately refresh deletion availability and explain its blocker
- Import's unchanged dirty guard has actionable guidance; resolve buttons use base availability so drafts cannot disable their own recovery
- Main guards and native cancellation still prevent writes; Serato's scope stays unchanged
