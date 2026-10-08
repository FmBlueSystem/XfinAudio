# Optional AI settings / Configuración segura de IA

[English](#credentials-stay-outside-settings) · [Español](#configuración-segura-en-español)

AI is off by default. The deterministic playlist tools remain available without a provider, key or network connection.

Open the **Ajustes de IA** panel from the workflow list. Nan Builders is the supported provider. The recipient host is shown, including a custom HTTPS endpoint supplied by the operator. Opening the panel, choosing a file, toggling the checkbox and cancelling never send a request.

## Credentials stay outside Settings

The app does not provide a key text field and does not write credential files. Configure `NAN_API_KEY` in the launch environment or in an operator-owned env file outside the app. Keep that file private with owner-only access; do not place it in a repository, shared folder, screenshot or support log. The app does not encrypt this file or repair its permissions. Use your trusted local credential-entry workflow; do not paste a secret into shell commands or chat.

An existing env file may contain a bare key or a `NAN_API_KEY` assignment. The default path is `~/.xfinaudio/apiIA.env`. **Elegir archivo de credenciales…** selects only its path; **Quitar fuente de credenciales** clears the custom path. The UI inspects presence, not the file contents. The adapter reads the credential only when an explicitly requested AI operation runs.

Environment credentials take precedence over file credentials. Existing launcher controls remain supported:
- `XFINAUDIO_AI_ENABLED` controls the initial enable override
- `XFINAUDIO_AI_ENV_FILE` controls the initial file override
- `NAN_API_BASE` selects an absolute HTTPS endpoint; credential-bearing redirects are rejected
- `NAN_MODEL` selects the provider model

The panel displays the effective initial enable/file overrides. **Guardar ajustes de IA** explicitly persists the selected preference and changes subsequent runtime requests immediately. A later relaunch still respects explicit launch overrides. Failed saves preserve prior preferences. No restart is required for AI changes; changing UI language retains its existing restart requirement.

## What is sent

Requested AI actions may send request text and track/set metadata such as titles, artists, genres, BPM, key, energy and transition/readiness summaries. They never send audio files. Dedicated local path fields are omitted; known and recognizable paths, including relative audio-file paths, are redacted from text. Arbitrary free text cannot be guaranteed free of private information, so avoid private details in prompts. The UI shows this disclosure before opt-in. The exact scope varies by action; see [the per-action data table](ai-workflows.md#data-sent-by-each-action). The optional panels start unconsented; changing the recipient resets that consent.

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
   para tu usuario. La app no cifra el archivo ni corrige sus permisos. No pegues
   claves en prompts, comandos de terminal, capturas, informes o conversaciones.
   La interfaz no tiene un campo para claves y guarda únicamente la ruta del archivo.
4. Activa la opción para las acciones que solicites. Si quieres comprobarla,
   **Probar conexión** envía solo el texto de prueba visible, el nombre del modelo
   y el identificador de la app, autenticados con tu credencial. Puede consumir
   cuota. No envía música ni metadata de tu biblioteca; tampoco guarda los ajustes
   ni habilita por sí sola otras acciones.
5. Pulsa **Guardar ajustes de IA** para conservar la preferencia. En cada
   asistencia, lee su contexto y destinatario antes de consentir y solicitar la
   llamada. No se envían archivos de audio. Los paneles requieren renovar el
   consentimiento si cambia el destinatario; habilitar IA en los ajustes no aplica
   filtros ni guarda playlists.

La clave del entorno tiene prioridad sobre la del archivo. `XFINAUDIO_AI_ENABLED`
y `XFINAUDIO_AI_ENV_FILE` pueden establecer preferencias al iniciar;
`NAN_API_BASE` cambia el destino HTTPS y `NAN_MODEL`, el modelo. Cambiar el destino
implica enviar las peticiones y la autenticación a ese destino: revísalo antes de
continuar. No se siguen redirecciones de las llamadas autenticadas.

Si falla la conexión, revisa la configuración fuera de la app y reintenta de
forma explícita. **Cancelar** o cerrar el panel ignora la respuesta pendiente,
pero no retira una petición que el proveedor ya recibió. Las funciones locales
siguen disponibles sin clave ni conexión.

Estas instrucciones describen el comportamiento implementado. La verificación
actual usa credenciales sintéticas y transportes inyectados; no certifica una
cuenta real de NaN. Consulta los [datos por acción y límites](ai-workflows.md).
