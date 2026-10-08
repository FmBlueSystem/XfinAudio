import { AI_CONNECTION_REQUEST, AI_RECIPIENT } from './optional-ai.js';
import type { AiSurface, OptionalAiController } from './optional-ai.js';
const make = <K extends keyof HTMLElementTagNameMap>(tag: K, text = '', className = ''): HTMLElementTagNameMap[K] => {
  const node = document.createElement(tag); node.textContent = text; node.className = className; return node;
};
const surfaceNames: Record<AiSurface, string> = { library: 'Biblioteca', prep: 'Preparación', review: 'Revisión', saved: 'Playlists guardadas', editor: 'Editor', metadata: 'Metadatos', live: 'Live', connection: 'Prueba de conexión' };
const surfaceDisclosure: Record<AiSurface, string> = {
  library: 'Se comparte la petición y el vocabulario de géneros para proponer filtros locales.',
  prep: 'Se comparte la petición y el vocabulario de géneros y estrategias. La selección y el orden se deciden con los motores locales.',
  editor: 'Se interpreta tu petición para preparar una propuesta que deberán validar las operaciones locales del editor.',
  saved: 'Se comparten identificadores anónimos y datos agregados de las playlists autorizadas; la comparación se realiza localmente.',
  review: 'Esta explicación comparte títulos, artistas, metadatos ordenados y hechos de calidad y preparación de la selección.',
  metadata: 'La explicación usa hechos y carencias de metadatos calculados localmente. No modifica etiquetas.',
  live: 'La explicación usa opciones y puntuaciones ya calculadas localmente. No cambia el orden, las marcas ni la reproducción.',
  connection: 'Prueba sintética sin datos de la biblioteca. Es una consulta explícita al proveedor y puede consumir cuota.',
};
// The improvement selector is a different authority than the legacy editor request: it
// shares real titles, artists, and bounded metadata, and optionally a replacement pool.
const improvementDisclosure = (includeReplacements: boolean): string => `Para proponer una mejora se comparten los títulos, artistas y metadatos musicales de las pistas seleccionadas${includeReplacements ? ' y el conjunto de posibles reemplazos autorizado para esta solicitud' : ', sin candidatas de reemplazo'}. No se envían rutas de archivos, identificadores estables ni audio. Aplicar la propuesta cambia solo el borrador; guardar la playlist sigue siendo una acción explícita y aparte.`;
export function createOptionalAiView(root: HTMLElement, controller: OptionalAiController, host: { canAct(): boolean; busy?(): boolean; idPrefix?: string; openSettings?(): void }): () => void {
  const prefix = host.idPrefix ?? 'optional-ai';
  const identify = <T extends HTMLElement>(node: T, suffix: string): T => { node.id = `${prefix}-${suffix}`; return node; };
  const canAct = (): boolean => host.canAct() && !controller.pending;
  // A local job holds the single core, not the instruction: the field stays editable so the
  // entered request survives the wait. An in-flight ask is different — its instruction is already
  // bound to the disclosed payload and the paid call, so it is frozen and the field disabled.
  const heldByLocalJob = (): boolean => controller.pending !== 'ask' && Boolean(host.busy?.());
  const localEditable = (): boolean => controller.requestEditable && (canAct() || heldByLocalJob());
  const section = make('section', '', 'surface prep-form'); section.setAttribute('aria-labelledby', `${prefix}-heading`);
  const heading = identify(make('h3'), 'heading');
  const error = identify(make('p', '', 'review-notice blocker'), 'error'); error.setAttribute('role', 'alert');
  const notice = identify(make('p', '', 'review-notice'), 'notice'); notice.setAttribute('role', 'status');
  const status = identify(make('p', '', 'field-hint'), 'status');
  const config = identify(make('details'), 'config');
  const configSummary = identify(make('summary'), 'config-summary'); config.append(configSummary);
  const enabled = identify(make('input'), 'enabled'); enabled.type = 'checkbox';
  const enabledLabel = make('label', 'Permitir solicitudes explícitas de asistencia IA'); enabledLabel.setAttribute('for', enabled.id);
  const autoAuthorize = identify(make('input'), 'auto-authorize'); autoAuthorize.type = 'checkbox';
  const autoAuthorizeLabel = make('label', 'No volver a preguntar en cada consulta (autorización automática)'); autoAuthorizeLabel.setAttribute('for', autoAuthorize.id);
  const dirty = identify(make('p', '', 'field-hint'), 'dirty'); dirty.setAttribute('aria-live', 'polite');
  const action = (id: string, caption: string, callback: () => void, primary = false): HTMLButtonElement => {
    const button = identify(make('button', caption, `button ${primary ? 'primary' : 'subtle'}`), id); button.type = 'button';
    button.addEventListener('click', () => { if (canAct() && !button.disabled) callback(); }); return button;
  };
  const settingsLink = action('settings-link', 'Abrir ajustes de IA', () => host.openSettings?.());
  const save = action('save', 'Guardar ajustes de IA', () => { void controller.save(); }, true);
  const discard = action('discard', 'Descartar cambios', () => controller.discard());
  const refresh = action('refresh', 'Actualizar ajustes', () => { void controller.load(); });
  const choose = action('choose', 'Elegir archivo de credenciales…', () => { void controller.chooseCredential(); });
  const clear = action('clear', 'Quitar fuente de credenciales', () => { void controller.clearCredential(); });
  enabled.addEventListener('change', () => { if (canAct()) controller.setEnabled(enabled.checked); });
  autoAuthorize.addEventListener('change', () => { if (canAct()) controller.setAutoAuthorize(autoAuthorize.checked); });
  const configActions = make('div', '', 'editor-actions'); configActions.append(save, discard, refresh, choose, clear);
  config.append(enabled, enabledLabel, autoAuthorize, autoAuthorizeLabel, identify(make('p', 'Con la autorización automática, cada consulta preparada se envía sin el diálogo del sistema. Puedes revertirla aquí en cualquier momento.', 'field-hint'), 'auto-authorize-hint'),
    make('p', 'El proveedor es Nan Builders. Estos ajustes guardan la fuente elegida, sin leer claves ni probar la conexión. Guarda o descarta el borrador antes de cambiar esa fuente. No pegues claves en la petición.', 'field-hint'), dirty, configActions);
  const recipient = identify(make('p', `Destinatario: Nan Builders · ${AI_RECIPIENT}`, 'review-notice'), 'recipient');
  const disclosure = identify(make('p', '', 'field-hint'), 'surface-disclosure');
  const requestField = identify(make('div'), 'request-field');
  const requestLabel = make('label', '¿Qué quieres consultar?'); requestLabel.setAttribute('for', `${prefix}-request`);
  const request = identify(make('textarea'), 'request'); request.maxLength = 2000; request.rows = 4; request.setAttribute('aria-describedby', `${prefix}-request-hint`);
  request.addEventListener('input', () => { if (localEditable()) controller.setRequest(request.value); });
  requestField.append(requestLabel, request, identify(make('p', 'Hasta 2000 caracteres. Revisa la versión redactada antes de autorizar el envío.', 'field-hint'), 'request-hint'));
  // Explicit improvement scope: off by default, invalidates any pending disclosure and
  // consent on change, and never contacts the provider by itself.
  const includeField = identify(make('div'), 'include-replacements-field');
  const include = identify(make('input'), 'include-replacements'); include.type = 'checkbox';
  const includeLabel = make('label', 'Incluir reemplazos'); includeLabel.setAttribute('for', include.id);
  include.addEventListener('change', () => { if (canAct()) controller.setIncludeReplacements(include.checked); });
  includeField.append(include, includeLabel, identify(make('p', 'Desactivado, la propuesta solo puede reordenar o quitar pistas del borrador. Activarlo amplía los datos divulgados y exige una autorización nueva.', 'field-hint'), 'include-replacements-hint'));
  const localHoldNotice = identify(make('p', '', 'review-notice'), 'local-hold'); localHoldNotice.setAttribute('role', 'status');
  const fixedRequest = identify(make('p', '', 'field-hint'), 'fixed-request');
  const prepare = action('prepare', 'Revisar datos antes de enviar', () => { void controller.prepare(); }, true);
  const prepareHint = identify(make('p', '', 'field-hint'), 'prepare-hint');
  const preview = identify(make('section'), 'preview'); preview.setAttribute('aria-labelledby', `${prefix}-preview-heading`);
  const previewRecipient = identify(make('p'), 'preview-recipient'); const disclosureList = make('ul'); const redacted = identify(make('p'), 'redacted-request');
  // The exact retained provider body is fetched only when the user opens this control. It is
  // read-only: no consent, no request, and no credential access is involved.
  const payload = identify(make('details'), 'payload');
  const payloadSummary = identify(make('summary', 'Ver payload exacto'), 'payload-summary');
  const payloadBody = identify(make('pre'), 'payload-body');
  const payloadHint = identify(make('p', 'Solo lectura local del cuerpo exacto que se enviaría al proveedor. No se envía nada al abrirlo.', 'field-hint'), 'payload-hint');
  payload.append(payloadSummary, payloadBody);
  payload.addEventListener('toggle', () => { if (payload.open && canAct() && !controller.pending) void controller.inspectPayload(); });
  const consent = identify(make('input'), 'consent'); consent.type = 'checkbox'; consent.checked = false;
  const consentLabel = make('label', 'Autorizo enviar esta solicitud y los datos descritos a Nan Builders'); consentLabel.setAttribute('for', consent.id);
  consent.setAttribute('aria-describedby', `${prefix}-consent-hint`); consent.addEventListener('change', () => { if (canAct()) controller.setConsent(consent.checked); });
  const ask = action('ask', 'Consultar IA…', () => { void controller.ask(); }, true);
  const consentHint = identify(make('p', '', 'field-hint'), 'consent-hint');
  preview.append(identify(make('h4', 'Vista previa del envío'), 'preview-heading'), previewRecipient, disclosureList, redacted, payload, payloadHint, consent, consentLabel,
    consentHint, ask);
  const pending = identify(make('p', 'Puedes cancelar desde el control de la operación. Los datos ya enviados no se pueden recuperar.', 'review-notice'), 'pending'); pending.setAttribute('role', 'status');
  const result = identify(make('section'), 'result'); result.setAttribute('aria-labelledby', `${prefix}-result-heading`);
  const resultHeading = identify(make('h4', 'Respuesta de IA'), 'result-heading'); const resultTitle = make('h5'); const resultText = make('p');
  const resultCaution = make('p', 'Contenido de IA para revisar. No es una evaluación del motor ni sustituye los metadatos o validadores locales.', 'review-notice');
  const proposal = make('details'); proposal.append(make('summary', 'Revisar datos de la propuesta')); const proposalText = make('pre'); proposal.append(proposalText);
  const apply = action('apply', 'Aplicar propuesta al trabajo local', () => { void controller.applySuggestion(); });
  const applyHint = identify(make('p', 'Aplicar no guarda, exporta ni reproduce audio. Esas acciones siguen siendo explícitas.', 'field-hint'), 'apply-hint');
  result.append(resultHeading, resultTitle, resultCaution, resultText, proposal, apply, applyHint);
  section.append(heading, error, notice, status, settingsLink, config, recipient, disclosure, requestField, includeField, localHoldNotice, fixedRequest, prepare, prepareHint, preview, pending, result); root.replaceChildren(section);
  let askTimer: ReturnType<typeof globalThis.setInterval> | null = null;
  const stopAskTimer = (): void => { if (askTimer !== null) globalThis.clearInterval(askTimer); askTimer = null; };
  const render = (): void => {
    const snapshot = controller.snapshot; const blocked = !canAct();
    config.hidden = controller.surface !== 'connection'; settingsLink.hidden = !config.hidden; settingsLink.disabled = blocked;
    configSummary.textContent = `Ajustes de asistencia IA${controller.dirty ? ' · cambios sin guardar' : ''}`;
    heading.textContent = `Asistencia IA opcional · ${surfaceNames[controller.surface]}`;
    error.hidden = !controller.error; error.textContent = controller.error; notice.hidden = !controller.notice; notice.textContent = controller.notice;
    status.textContent = !snapshot ? 'Carga los ajustes para conocer el estado de la asistencia.'
      : `${snapshot.enabled ? 'Asistencia activada solo para solicitudes explícitas.' : 'Asistencia desactivada.'} ${snapshot.configured ? `Fuente seleccionada: ${snapshot.credentialLabel ?? 'archivo autorizado'}. ${controller.result?.kind === 'connection' ? 'Consulta el resultado de la prueba; seleccionar una fuente no garantiza la conexión.' : 'No se ha comprobado la conexión.'}` : 'No hay una fuente de credenciales seleccionada.'}`;
    enabled.checked = snapshot?.enabled ?? false; enabled.disabled = blocked || !snapshot;
    autoAuthorize.checked = snapshot?.autoAuthorize ?? false; autoAuthorize.disabled = blocked || !snapshot;
    dirty.textContent = controller.dirty ? 'Cambios de IA sin guardar. Se conservan al navegar.' : 'Sin ajustes de IA pendientes.';
    save.disabled = blocked || !controller.canSave; discard.disabled = blocked || !controller.dirty; refresh.disabled = blocked;
    choose.disabled = blocked || !snapshot || controller.dirty; clear.disabled = blocked || !snapshot?.configured || controller.dirty;
    disclosure.textContent = controller.improvementEditor ? improvementDisclosure(controller.includeReplacements) : surfaceDisclosure[controller.surface]; requestField.hidden = !controller.requestEditable;
    // The consent copy must name the authority actually in force: with persisted automatic
    // authorization no system dialog appears, so the hint must not claim one.
    consentHint.textContent = snapshot?.autoAuthorize === true
      ? 'Esta autorización vale solo para esta solicitud. Con la autorización automática activada en Ajustes, continuar envía la consulta directamente, sin el diálogo del sistema. Preparar esta vista no contacta al proveedor.'
      : 'Esta autorización vale solo para esta solicitud. Al continuar también se pide confirmación en el diálogo del sistema. Preparar esta vista no contacta al proveedor.';
    // The improvement prompt is only truthful for the improvement selector; the legacy
    // editor keeps its four-operation framing.
    const improvement = controller.improvementEditor;
    requestLabel.textContent = improvement ? 'Mejorar esta playlist' : '¿Qué quieres consultar?';
    request.placeholder = improvement ? 'Ej.: abre con algo más energético y quita las pistas lentas' : '';
    includeField.hidden = !improvement; include.checked = controller.includeReplacements; include.disabled = blocked || !improvement;
    request.disabled = !localEditable(); if (request.value !== controller.request) request.value = controller.request;
    localHoldNotice.hidden = !heldByLocalJob() || controller.pending === 'ask';
    localHoldNotice.textContent = controller.requestEditable ? 'Hay una operación local en curso. Puedes conservar tu petición en este campo; la vista previa se habilitará cuando termine.' : 'Hay una operación local en curso. Espera a que termine para continuar con la asistencia IA.';
    fixedRequest.hidden = controller.requestEditable; fixedRequest.textContent = controller.surface === 'connection' ? AI_CONNECTION_REQUEST : 'Solicitud fija: explicar los hechos de esta pantalla, sin añadir una petición libre.';
    const blocker = controller.prepareBlocker();
    prepare.disabled = blocked || !controller.canPrepare;
    prepareHint.textContent = prepare.disabled ? blocker : ''; prepareHint.hidden = !prepare.disabled || !blocker;
    preview.hidden = !controller.preview;
    disclosureList.replaceChildren(); if (controller.preview) { previewRecipient.textContent = `Destinatario: ${controller.preview.recipient}`; for (const line of controller.preview.disclosure) disclosureList.append(make('li', line)); redacted.textContent = controller.preview.requestPreview; }
    payload.hidden = !controller.preview;
    payloadSummary.setAttribute('aria-disabled', String(blocked || controller.pending !== null));
    payloadBody.textContent = controller.payload ? controller.payload.body : '';
    payloadHint.textContent = `${controller.payload?.truncated ? 'El cuerpo supera el límite y se muestra truncado. ' : ''}Solo lectura local del cuerpo exacto que se enviaría al proveedor. No se envía nada al abrirlo.`;
    consent.checked = controller.consent; consent.disabled = blocked || !controller.preview; ask.disabled = blocked || !controller.canAsk; ask.textContent = controller.surface === 'connection' ? 'Probar conexión…' : 'Consultar IA…';
    const phase = controller.pendingPhaseText; pending.hidden = controller.pending === null;
    if (controller.pending === 'ask') {
      const seconds = controller.askElapsedSeconds(Date.now());
      pending.textContent = `${seconds === null ? phase : `${phase} · ${seconds} s`} Puedes cancelar desde el control de la operación. Los datos ya enviados no se pueden recuperar.`;
      if (askTimer === null) askTimer = globalThis.setInterval(render, 1000);
    } else { stopAskTimer(); pending.textContent = phase; }
    result.hidden = !controller.result;
    const value = controller.result; if (value) { resultTitle.textContent = value.title; resultText.textContent = value.text; proposal.hidden = value.proposal === null; proposalText.textContent = value.proposal === null ? '' : JSON.stringify(value.proposal, null, 2); }
    // The improvement action only asks the local validators for a bounded preview; it must
    // not imply the draft changed. Other surfaces keep their original applied wording.
    const improvementResult = controller.improvementEditor;
    apply.textContent = improvementResult ? 'Revisar propuesta local' : 'Aplicar propuesta al trabajo local';
    applyHint.textContent = improvementResult ? 'Revisar la propuesta local no cambia el borrador: el editor muestra el antes y el después para que decidas si aplicarla y cuándo guardarla.' : 'Aplicar no guarda, exporta ni reproduce audio. Esas acciones siguen siendo explícitas.';
    resultCaution.textContent = improvementResult ? 'Propuesta pendiente de revisión local. El editor muestra el antes y el después con la evaluación del motor; nada cambia hasta que la apliques en el borrador.' : 'Contenido de IA para revisar. No es una evaluación del motor ni sustituye los metadatos o validadores locales.';
    apply.hidden = !value?.canApply; apply.disabled = blocked || !controller.canApply;
  };
  return render;
}
