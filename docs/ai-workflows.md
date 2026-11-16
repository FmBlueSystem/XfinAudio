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
The new optional panels start unconsented; a recipient change requires fresh consent.

A request already sent may finish after cancellation. Cancellation prevents its
result from being applied; it cannot recall a request received by the provider.
A changed library, request, set or relevant constraint invalidates stale results.

A list conversation asks consent once: the native dialog appears on the first turn
of a conversation and later turns of the same conversation are sent without it,
because every turn discloses the same class of data. The **No volver a preguntar en
cada consulta** setting keeps its meaning. A new conversation — **Nueva
conversación**, a change of the AI settings or of the credential file, or anything
that discards the generated list — asks consent again.

## Data sent by each action

| Action | Disclosed provider context |
|---|---|
| Library | request text and sanitized genre vocabulary; no track list |
| Create | request and genres; titles only when explicitly selected for that request |
| Review | ordered track titles, artists, BPM, key and energy, computed transitions, warnings and readiness summaries |
| List chat | ordered titles, artists, genres, BPM, key, energy and duration per track; every transition with its score, explanations and warnings; readiness status with blockers; protected opening/closing/required positions; the question and the previous turns of the conversation; no file paths or track ids |
| Editor | request text only; no saved playlist or track list |
| My Playlists | request with known saved names replaced by temporary IDs, plus anonymous aggregate descriptors; no persistent IDs |
| Metadata | aggregate track/missing-field counts and count of locked tracks with gaps |
| Live | temporary candidate IDs, existing ranks/scores, defined BPM/energy gaps and readiness facts |

No action uploads audio. Dedicated path fields are omitted and known/recognizable
paths are redacted from text; arbitrary private text cannot be reliably removed.
Do not type secrets or private details into a request. Commentary can still be
wrong; validation of a response's shape does not prove its musical relevance.
My Playlists limits semantic context to 200 saved sets and directs larger
collections to local search without a provider call.

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
- **List chat:** «Asistente de lista» answers questions about the generated list
  from the same evidence, rebuilt on every turn, so an edit between two turns is
  what the assistant reads next. The conversation lives in memory only and is
  never written to disk; it survives list edits and ends with a new conversation,
  a settings or credential change, a discarded list, or a core restart. A reply
  may propose up to five changes (replace a track with the engine's candidate, or
  move a track); the core validates them and shows them under «Cambios
  propuestos». Nothing changes until the user presses «Aplicar» on a card; the
  change then goes through the normal review edit, can be undone with
  «Deshacer», and never contacts the provider. The assistant is also told how
  many tracks were requested, the engine warnings and the other alternatives
  (track count and score), and may propose extending the list or using another
  alternative; extending adds tracks the engine picks from the library. The
  assistant may also ask for one round of local library searches per message
  (up to two searches, up to 20 results each); the title, artist, genre, BPM,
  key, energy and duration of the tracks found are then sent to the provider,
  never a path or an identifier. With those results it can propose removing a
  track, adding or swapping in a track it found, reordering, or undoing the
  last change. It lives in a floating window opened from the bot button of the
  review screen. The assistant cannot save or
  export anything
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
- Asistente de lista: «¿Qué transiciones son las más débiles?» o «¿Qué pista
  quitarías y por qué?». Responde en español leyendo la lista, sus transiciones y
  sus avisos; pregúntale otra cosa para seguir la misma conversación

## Privacidad y control en español

La IA recibe únicamente el contexto indicado para la acción elegida. Biblioteca
comparte la petición y géneros saneados; Editor, solo la petición. Mis playlists
sustituye nombres conocidos por IDs temporales y usa descriptores agregados;
limita el contexto a 200 sets guardados y ofrece búsqueda local por encima de ese
límite. Metadatos comparte cantidades y faltantes; Live, candidatos anónimos con
puntuaciones y hechos ya calculados.

Crear comparte petición y géneros, con títulos solo si lo eliges para esa petición.
Revisar puede compartir títulos, artistas, BPM, tonalidad, energía y resúmenes de
transiciones/validación del set. El Asistente de lista envía además géneros,
duración, cada transición con su puntuación y avisos, el estado de preparación con
sus bloqueos, las posiciones protegidas (apertura, cierre, obligatorias), tu
pregunta y los turnos anteriores de la conversación. Esa conversación se guarda
solo en memoria: no se escribe en disco, sobrevive a las ediciones de la lista y
termina con «Nueva conversación», con un cambio de los ajustes o de la credencial,
con la lista descartada o al cerrar la app. No asumas que todas las pantallas son anónimas:
revisa su aviso antes de enviar. Nunca se envía audio. Se ocultan rutas conocidas
o reconocibles, pero el texto libre puede contener información privada que no se
pueda detectar; no la incluyas.

El consentimiento de la conversación se pide una vez: el diálogo nativo aparece en
el primer turno y no se repite en los siguientes de la misma conversación, porque
cada turno envía la misma clase de datos. La opción **No volver a preguntar en cada
consulta** conserva su significado. Una conversación nueva vuelve a pedir
consentimiento.

El motor local sigue decidiendo el orden, las restricciones y la disponibilidad.
En Editor, aplicar una propuesta cambia el borrador; guardar es otra acción.
En Live, indicar la pista actual es una acción manual, no es detección automática de reproducción.
Las diferencias de BPM se expresan como porcentaje simétrico absoluto con
normalización half-time; la distancia de energía no indica por sí sola subida o
bajada. Una puntuación local no es una probabilidad.

La exportación directa a Serato mantiene vista previa, confirmación, copias,
validación y recuperación; ningún comentario IA escribe crates o modifica la base
Serato V2 activa. El comportamiento de loudness es independiente: su opción,
activada por defecto, puede escribir tags y reemplazar comentarios automáticamente.

Ante errores, usa **Configurar IA**, continúa localmente o reintenta explícitamente.
Cancelar evita aplicar respuestas tardías; no borra lo ya recibido por el proveedor.
Las pruebas sintéticas no sustituyen una conexión NaN real, escucha musical,
importación real en Serato ni QA interactiva en macOS.

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
