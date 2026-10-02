# Observable requirements
- GIVEN a readable supported audio stream WHEN scanned THEN Library shows its parser-confirmed format, codec where relevant, and positive finite declared bitrate in kbps; optional fields never affect metadata readiness.
- GIVEN old, missing or invalid audio properties WHEN displayed THEN the unavailable field reads “No disponible”; filenames never manufacture encoding.
- GIVEN variable/average bitrate mode confirmed by metadata WHEN shown THEN it is identified as VBR/ABR, never mislabeled fixed; declared rates are identified as such rather than measured file averages.
- GIVEN an existing version-6 database WHEN opened THEN tracks and their ordering survive an additive migration and new fields remain absent until scanning; new values survive restart and rescan corrections.
- GIVEN each actual Library data column WHEN its header is activated THEN ascending toggles to descending with visible arrow and aria-sort; native buttons support keyboard. Index and listening controls are not data sort keys.
- GIVEN equal or missing values WHEN sorting either way THEN ties are deterministic and missing values stay last; numeric values use numeric order.
- GIVEN filters/duplicate suppression and a large Library WHEN sorted THEN all matching rows participate, without changing recommendation ranking, saved order, playback, selection or filters.
- GIVEN local sort controls and header sorting WHEN either is used THEN both reflect one applied order; stale or failed replies cannot falsely label the rows.
