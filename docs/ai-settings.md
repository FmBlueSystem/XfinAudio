# Optional AI settings / Configuración segura de IA

[English](#credentials-stay-outside-settings) · [Español](#configuración-segura-en-español)

AI is off by default. The deterministic playlist tools remain available without a provider, key or network connection.

Open the **Ajustes de IA** panel from the workflow list. Nan Builders is the supported provider. The recipient host is shown, including a custom HTTPS endpoint supplied by the operator. Opening the panel, choosing a file, toggling the checkbox and cancelling never send a request.

## Credentials stay outside Settings

The app does not provide a key text field and does not write credential files. Configure `NAN_API_KEY` in the launch environment or in an operator-owned env file outside the app. Keep that file private with owner-only access; do not place it in a repository, shared folder, screenshot or support log. The app does not encrypt this file or change its permissions.

The credential file must be readable only by your account: mode `0600` (`0400` also works). A file that grants any group or other permission — for example `0644` or `0640` — is refused before a single byte is read, with the error code `ai_credential_permissions`, and the request is never sent. Fix it with `chmod 600` on that file and request again; the message never contains the path or the key. Use your trusted local credential-entry workflow; do not paste a secret into shell commands or chat.

An existing env file may contain a bare key or a `NAN_API_KEY` assignment. The default path is `~/.xfinaudio/apiIA.env`. **Elegir archivo de credenciales…** selects only its path; **Quitar fuente de credenciales** clears the custom path. The UI inspects presence, not the file contents. The adapter reads the credential only when an explicitly requested AI operation runs.

Environment credentials take precedence over file credentials. Existing launcher controls remain supported:
- `XFINAUDIO_AI_ENABLED` controls the initial enable override
- `XFINAUDIO_AI_ENV_FILE` controls the initial file override
- `NAN_API_BASE` selects an absolute HTTPS endpoint; credential-bearing redirects are rejected
- `NAN_MODEL` selects the provider model

The panel displays the effective initial enable/file overrides. **Guardar ajustes de IA** explicitly persists the selected preference and changes subsequent runtime requests immediately. A later relaunch still respects explicit launch overrides. Failed saves preserve prior preferences. No restart is required for AI changes; changing UI language retains its existing restart requirement.

The panel also offers **No volver a preguntar en cada consulta** — persisted automatic authorization, off by default. With it on, an already prepared query is sent without the per-send native confirmation dialog; turn it off in the panel to restore the dialog. Preparing a query still shows its disclosure first, and every other explicit action (connection test, credential changes, save/export) keeps its own confirmation. The native confirm dialog itself offers the same checkbox; ticking it and confirming persists the preference best-effort.

A list conversation asks its own consent once, independently of that setting: the native dialog appears on the first turn of a conversation and later turns of the same conversation are sent without it, because each turn discloses the same class of data. The conversation is kept in memory only. Saving different AI settings or choosing a different credential file starts a new conversation, so consent is asked again; the same applies to **Nueva conversación**, to discarding the generated list and to restarting the app.

## What is sent

Requested AI actions may send request text and track/set metadata such as titles, artists, genres, BPM, key, energy and transition/readiness summaries. They never send audio files. The list chat additionally sends your question and the previous turns of that conversation; the conversation is kept in memory only and is never written to disk. Dedicated local path fields are omitted; known and recognizable paths, including relative audio-file paths, are redacted from text. Arbitrary free text cannot be guaranteed free of private information, so avoid private details in prompts. The UI shows this disclosure before opt-in. The exact scope varies by action; see [the per-action data table](ai-workflows.md#data-sent-by-each-action). The optional panels start unconsented; changing the recipient resets that consent.

**Probar conexión** sends only `Reply with OK. XfinAudio connection test.`, plus the selected model name and app identifier, authenticated with the configured credential. No library content is sent. This may consume provider quota. Testing uses the staged configuration and does not save it or enable other AI actions.

A configuration-present status is not a connection success. Missing or invalid credentials, rejected authentication, malformed responses and network failures display recovery guidance, while offline tools continue working. The connection status never echoes raw provider response text or transport errors.

The test runs in the background. Duplicate clicks are blocked. Cancelling the test, closing the panel or editing the configuration discards pending results. An already sent request cannot be recalled; retry becomes available when that bounded request finishes.

## Verification boundary

Development and automated tests use synthetic credentials, fake responses and injected transports only. They validate the interaction and security boundaries; they do not verify a real subscription, key or provider connection.

## Configuración segura en español

La IA está desactivada por defecto. NaN (Nan Builders) es el proveedor integrado;
el destino predeterminado es `api.nan.builders`. Las acciones configuradas y
solicitadas explícitamente pueden hacer peticiones reales. Tener una configuración
presente no demuestra que la clave funcione ni que exista una suscripción válida.

1. Abre el panel **Ajustes de IA** desde la lista de flujos. Comprueba el
   destinatario mostrado. Abrir el panel no envía la biblioteca ni hace una
   llamada al proveedor.
2. Configura la credencial fuera de XfinAudio mediante tu procedimiento local de
   confianza. Se admite `NAN_API_KEY` en el entorno de inicio o un archivo env
   privado de tu propiedad. La ruta predeterminada es `~/.xfinaudio/apiIA.env`;
   **Elegir archivo de credenciales…** selecciona otra ruta, sin importar su
   contenido.
3. Mantén el archivo fuera de repositorios y carpetas compartidas, con acceso solo
   para tu usuario. El archivo debe tener modo `0600` (también vale `0400`): si
   concede cualquier permiso a grupo u otros — por ejemplo `0644` o `0640` — la app
   lo rechaza antes de leer un solo byte, con el código de error
   `ai_credential_permissions`, y no llega a enviar la petición. Corrígelo con
   `chmod 600` sobre ese archivo y vuelve a solicitarla; el mensaje nunca incluye la
   ruta ni la clave. La app no cifra el archivo ni corrige sus permisos por su
   cuenta. No pegues claves en prompts, comandos de terminal, capturas, informes o
   conversaciones. La interfaz no tiene un campo para claves y guarda únicamente la
   ruta del archivo.
4. Activa la opción para las acciones que solicites. Si quieres comprobarla,
   **Probar conexión** envía solo el texto de prueba visible, el nombre del modelo
   y el identificador de la app, autenticados con tu credencial. Puede consumir
   cuota. No envía música ni metadata de tu biblioteca; tampoco guarda los ajustes
   ni habilita por sí sola otras acciones.
5. Pulsa **Guardar ajustes de IA** para conservar la preferencia. En cada
   asistencia, lee su contexto y destinatario antes de consentir y solicitar la
   llamada. No se envían archivos de audio. Los paneles requieren renovar el
   consentimiento si cambia el destinatario; habilitar IA en los ajustes no aplica
   filtros ni guarda playlists. El Asistente de lista pide su propio consentimiento
   una vez: el diálogo aparece en el primer turno y no se repite en los siguientes
   de la misma conversación, que se guarda solo en memoria. Guardar otros ajustes de
   IA o elegir otro archivo de credenciales inicia una conversación nueva y vuelve a
   pedir consentimiento; también «Nueva conversación», descartar la lista generada
   o reiniciar la app.

Opcional: la casilla **No volver a preguntar en cada consulta** guarda la
autorización automática (desactivada por defecto). Activada, una consulta ya
preparada se envía sin repetir el diálogo de confirmación nativo; desactívala en
el panel para recuperarlo. Preparar la consulta sigue mostrando su aviso de datos,
y las demás acciones explícitas (prueba de conexión, cambios de credencial,
guardar/exportar) conservan sus confirmaciones. El diálogo nativo de confirmación
ofrece la misma casilla; márcala y confirma para persistir la preferencia de
forma best-effort. La conversación de la lista no depende de esta casilla: pide
consentimiento en su primer turno y lo omite en los siguientes de esa conversación,
porque cada turno envía la misma clase de datos.

La clave del entorno tiene prioridad sobre la del archivo. `XFINAUDIO_AI_ENABLED`
y `XFINAUDIO_AI_ENV_FILE` pueden establecer preferencias al iniciar;
`NAN_API_BASE` cambia el destino HTTPS y `NAN_MODEL`, el modelo. Cambiar el destino
implica enviar las peticiones y la autenticación a ese destino: revísalo antes de
continuar. No se siguen redirecciones de las llamadas autenticadas.

Si falla la conexión, revisa la configuración fuera de la app y reintenta de
forma explícita. **Cancelar** o cerrar el panel ignora la respuesta pendiente,
pero no retira una petición que el proveedor ya recibió. Las funciones locales
siguen disponibles sin clave ni conexión.

## Asistente de lista: espera, cancelación y avisos

Mientras un turno del Asistente de lista está en curso, el chat muestra el tiempo
transcurrido y la fase exacta: preparar la solicitud, esperar el diálogo de
confirmación del sistema, esperar la respuesta de la IA y aplicar los cambios
propuestos. Ofrece **Cancelar** durante el envío: el turno termina, la app queda
disponible y la lista no cambia; la pregunta sigue en el campo para reintentarla.
Una respuesta que llegue después de cancelar se descarta y no modifica nada.

Cada llamada al proveedor tiene un límite propio (120 s en el chat, menos en las
demás acciones). Si se agota, el turno termina con el aviso
«El proveedor no respondió a tiempo…» y no se aplica nada; el servicio local
sigue funcionando y se puede reintentar cuando quieras. Un turno nunca espera
más que ese límite por cada llamada que hace, incluida la segunda consulta de
una búsqueda.

El chat también dice, en español, lo que antes se perdía en silencio: cuando la
aplicación automática no pudo aplicar ningún cambio de la respuesta, cuando el
diálogo no pudo guardar la preferencia «No volver a preguntar en cada consulta»,
cuando no se pudo comprobar la autorización automática y cuando un cambio
propuesto ya no está disponible o hay una operación en curso. Los textos no
implican que algo se haya aplicado: la lista solo cambia con un cambio aplicado
y anunciado.

Estas instrucciones describen el comportamiento implementado. La verificación
actual usa credenciales sintéticas y transportes inyectados; no certifica una
cuenta real de NaN. Consulta los [datos por acción y límites](ai-workflows.md).
