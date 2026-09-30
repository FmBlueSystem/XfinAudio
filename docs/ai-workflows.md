# Optional AI workflows / Flujos opcionales de IA

XfinAudio keeps musical decisions in its local engine. The optional configured
NaN provider interprets requests or explains already-computed evidence. It does
not choose arbitrary filesystem paths, write tags, mix audio, export crates or
silently save edits. Local tools remain available with AI disabled or offline.

## Configuration and consent

See [AI Settings](ai-settings.md). AI is disabled by default. Configure the
credential outside the application, enable the preference explicitly, then use
only the AI action whose disclosure you accept. Each additional assistant shows
what context it sends and the configured recipient. No audio files are uploaded.
Connection tests send disclosed synthetic text and can consume provider quota.

A request already sent may finish after cancellation. Cancellation prevents its
result from being applied; it cannot recall a request received by the provider.
A changed library, request, set or relevant constraint invalidates stale results.

## Screen boundaries

- **Library:** local interpretation supports explicit English/Spanish filters.
  The optional provider interprets broader language into the same editable filter
  model. Missing BPM, key and energy remain unknown; filters never create values
- **Create:** AI interpretation is shown as duration, style, strategy and hard
  constraints. Edit or confirm before local variant generation. Applying a variant
  remains a separate action. Titles are excluded from the default context
- **Review:** engine facts, risks and replacement previews work locally. Optional
  narration receives computed evidence. Treat its text as commentary to verify
  against the visible facts; it cannot apply a replacement or change the set
- **My Playlists:** local search and comparisons use saved sets and known metadata.
  Optional AI interprets semantic queries using anonymous set IDs and aggregates;
  the displayed comparison is still computed locally from the selected known sets
- **Editor:** local or AI-interpreted shortening/energy requests produce a musical
  preview. Apply changes only the draft; Save changes the saved playlist. Locked
  and excluded tracks are enforced. Unknown metadata can block validation. A dirty
  draft must be saved or explicitly discarded before opening another set or closing
- **Metadata:** repair priorities are computed locally from actual missing fields.
  Optional commentary explains those gaps and priorities. Correct values must come
  from verified sources; no assistant fills or writes missing tags
- **Live:** only an applied engine-ready set can start a manual guidance session.
  Candidate scores/ranking are local and revalidated. Optional commentary explains
  the current computed candidates. It cannot alter ranking or identify playback
- **Export:** the direct deterministic Serato workflow is unchanged, including
  preview, explicit export, backups and validation. No AI writes export files

The owner's existing loudness policy is unchanged: its enabled setting can write
loudness tags automatically and replace comments. These AI workflows do not add
another audio-write path or disable that separately documented behavior.

## Ejemplos para revisar

- Biblioteca: «house suave para abrir». La interpretación local sugiere un rango
  de energía visible y editable; la opción IA admite peticiones más abiertas
- Crear: «45 minutos de house para apertura». Revisa lo entendido antes de generar
- Editor: «acorta a 10 temas» o «sube gradualmente la energía». Examina la propuesta,
  aplica al borrador y guarda solo si quieres conservar el cambio
- Mis playlists: describe el set que buscas o compara dos sets guardados. Si faltan
  duraciones o energía, la comparación lo indica en lugar de rellenar los datos

## Recovery and verification limits

Use Configure AI for disabled/missing credentials and provider errors. Retry is
explicit; no background retry sends additional content. A failed AI action does
not replace an existing local result. Do not paste credentials into request text.

Automated tests use synthetic metadata and injected transports. They verify
request shapes, validation, consent, state isolation and failure recovery. They
do not establish real-provider availability, musical taste, listening quality or
native macOS rendering/installation. Generated commentary can be inaccurate even
when its supplied evidence is correct; the engine's displayed facts remain the
source of truth.
