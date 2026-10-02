# Integration design

Independent worktrees own Settings, Library/Create, Editor/Playlists, Review/Live.
The coordinator owns Metadata and desktop shell navigation/state wiring. No new
provider dependency is introduced. Local interpretations/explanations are labeled
as local and only use known metadata; remote content uses existing secure adapter.

Repair guidance derives missing values from MetadataGapReport, prioritizes current
locked tracks, then tracks needing fewer field repairs, with stable path tie-break.
It is display-only and explicitly directs verified external corrections/rescan.

Shell additions append Editor so existing numerical screen indices remain stable.
Live readiness is delegated to a local domain predicate shared by navigation/UI.
AI configuration route is a signal to the Settings controller, not a shell command.
