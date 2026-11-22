import { AI_RECIPIENT } from './optional-ai.js';
import { LIST_CHAT_AUTO, LIST_CHAT_PROPOSED, LIST_CHAT_READ_AGAIN, LIST_CHAT_UNDO_BATCH, listChatActionText, listChatDropped, listChatPeriodKept } from './list-chat.js';
import type { ListChatController } from './list-chat.js';
/** S7's exact copy: the empty state and the three questions that only fill the box. */
export const LIST_CHAT_EMPTY = 'Pregunta cómo mejorar esta lista. El asistente lee las pistas, las transiciones y los avisos.';
export const LIST_CHAT_EXAMPLES = ['¿Qué transiciones son las más débiles?', '¿Qué pista quitarías y por qué?', '¿Cómo mejoro la curva de energía?'] as const;
export const LIST_CHAT_DISCLOSURE = 'El asistente lee la lista y la conversación con Nan Builders: se comparten los títulos, artistas y metadatos de la lista, sus transiciones, la preparación y los avisos; nunca rutas de archivo ni identificadores de pista. Los cambios se aplican en tu equipo y se pueden deshacer.';
/** S2's batch action, offered only with two or more proposed changes. */
export const LIST_CHAT_APPLY_ALL = 'Aplicar todo';
const make = <K extends keyof HTMLElementTagNameMap>(tag: K, text = '', className = ''): HTMLElementTagNameMap[K] => {
  const node = document.createElement(tag); node.textContent = text; node.className = className; return node;
};
const roleName: Record<'user' | 'assistant', string> = { user: 'Tú', assistant: 'Asistente' };
/**
 * The «Asistente de lista» panel for the review screen: the stored conversation oldest first,
 * one question box, «Enviar» and «Nueva conversación», the changes the last reply proposes,
 * plus the disclosure of the last prepared turn and its read-only exact-body viewer. Every
 * value is set as text, never as markup.
 */
export function createListChatView(root: HTMLElement, controller: ListChatController, options: { idPrefix?: string; hideHeading?: boolean } = {}): () => void {
  const prefix = options.idPrefix ?? 'list-chat';
  const identify = <T extends HTMLElement>(node: T, suffix: string): T => { node.id = `${prefix}-${suffix}`; return node; };
  const section = make('section', '', 'surface prep-form list-chat');
  if (!options.hideHeading) section.setAttribute('aria-labelledby', `${prefix}-heading`);
  const heading = identify(make('h3', 'Asistente de lista'), 'heading');
  if (options.hideHeading) heading.hidden = true;
  const error = identify(make('p', '', 'review-notice blocker'), 'error'); error.setAttribute('role', 'alert');
  const notice = identify(make('p', '', 'review-notice'), 'notice'); notice.setAttribute('role', 'status');
  // S15: what the last period change replaced and the tracks that are still out of period.
  const periodReport = identify(make('section', '', 'list-chat-period'), 'period');
  const periodNotice = identify(make('p', '', 'review-notice'), 'period-notice'); periodNotice.setAttribute('role', 'status');
  const periodKeptHeading = identify(make('p', '', 'field-hint'), 'period-kept-heading');
  const periodKeptList = identify(make('ul', '', 'list-chat-period-kept'), 'period-kept');
  periodReport.append(periodNotice, periodKeptHeading, periodKeptList);
  // S9: the window applies every reply at once unless the DJ turns this switch off.
  const auto = identify(make('div', '', 'editor-actions list-chat-auto'), 'auto');
  const autoLabel = make('label', LIST_CHAT_AUTO); autoLabel.setAttribute('for', `${prefix}-auto-toggle`);
  const autoToggle = identify(make('input'), 'auto-toggle'); autoToggle.type = 'checkbox';
  autoToggle.addEventListener('change', () => controller.setAutoApply(autoToggle.checked));
  auto.append(autoLabel, autoToggle);
  // What the last automatic batch applied, in the same sentences as its cards, and one undo for it.
  const autoApplied = identify(make('section', '', 'list-chat-applied'), 'auto-applied');
  const autoNotice = identify(make('p', '', 'review-notice'), 'auto-notice'); autoNotice.setAttribute('role', 'status');
  const autoList = identify(make('ul', '', 'list-chat-applied-list'), 'auto-list');
  const undoBatch = identify(make('button', LIST_CHAT_UNDO_BATCH, 'button subtle'), 'undo-batch'); undoBatch.type = 'button';
  undoBatch.addEventListener('click', () => { if (!undoBatch.disabled) void controller.undoBatch(); });
  autoApplied.append(autoNotice, autoList, undoBatch);
  const empty = identify(make('p', LIST_CHAT_EMPTY, 'field-hint'), 'empty');
  const examples = identify(make('div', '', 'editor-actions'), 'examples');
  const action = (id: string, caption: string, callback: () => void, primary = false): HTMLButtonElement => {
    const button = identify(make('button', caption, `button ${primary ? 'primary' : 'subtle'}`), id); button.type = 'button';
    button.addEventListener('click', () => { if (!button.disabled) callback(); }); return button;
  };
  LIST_CHAT_EXAMPLES.forEach((example, index) => examples.append(action(`example-${index}`, example, () => controller.setRequest(example))));
  const conversation = identify(make('ol', '', 'list-chat-conversation'), 'conversation');
  // The changes the last reply proposes live under it: one card each, and the count of the
  // items the core dropped because they could never be applied.
  const proposed = identify(make('section'), 'proposed');
  const proposedHeading = identify(make('h4', LIST_CHAT_PROPOSED), 'proposed-heading');
  const proposedCards = identify(make('ul', '', 'list-chat-actions'), 'proposed-actions');
  const applyAll = identify(make('button', LIST_CHAT_APPLY_ALL, 'button subtle'), 'apply-all'); applyAll.type = 'button';
  applyAll.addEventListener('click', () => { if (!applyAll.disabled) void controller.applyAll(); });
  const dropped = identify(make('p', '', 'review-notice'), 'dropped');
  proposed.append(proposedHeading, proposedCards, applyAll, dropped);
  const requestField = identify(make('div'), 'request-field');
  const requestLabel = make('label', 'Pregunta sobre esta lista'); requestLabel.setAttribute('for', `${prefix}-request`);
  const request = identify(make('textarea'), 'request'); request.maxLength = 2000; request.rows = 3; request.setAttribute('aria-describedby', `${prefix}-disclosure`);
  request.addEventListener('input', () => { if (controller.requestEditable) controller.setRequest(request.value); });
  requestField.append(requestLabel, request);
  const actions = identify(make('div', '', 'editor-actions'), 'actions');
  const send = action('send', 'Enviar', () => { void controller.send(); }, true);
  const reset = action('reset', 'Nueva conversación', () => { void controller.newConversation(); });
  // S1: the turn's own way out. It is offered only while the chat is sending and stops exactly that turn.
  const cancel = action('cancel', 'Cancelar', () => controller.cancel());
  actions.append(send, reset, cancel);
  const pending = identify(make('p', '', 'review-notice'), 'pending'); pending.setAttribute('role', 'status');
  // S3: what the system could not store about this turn, in plain Spanish.
  const warnings = identify(make('ul', '', 'review-notice list-chat-warnings'), 'warnings');
  warnings.setAttribute('role', 'status');
  const disclosure = identify(make('p', LIST_CHAT_DISCLOSURE, 'field-hint'), 'disclosure');
  // The disclosure of the turn that is already prepared, and the exact body on demand: both
  // read-only, and inspecting them never sends anything.
  const prepared = identify(make('section'), 'prepared');
  const previewRecipient = identify(make('p', `Destinatario: Nan Builders · ${AI_RECIPIENT}`, 'review-notice'), 'preview-recipient');
  const previewLines = identify(make('ul'), 'preview-lines');
  const payload = identify(make('details'), 'payload');
  const payloadSummary = identify(make('summary', 'Ver lo que se envía'), 'payload-summary');
  const payloadBody = identify(make('pre'), 'payload-body');
  const payloadHint = identify(make('p', 'Solo lectura local del cuerpo exacto que se enviaría al proveedor. Abrirlo no envía nada.', 'field-hint'), 'payload-hint');
  payload.append(payloadSummary, payloadBody, payloadHint);
  payload.addEventListener('toggle', () => { if (payload.open) void controller.inspectPayload(); });
  prepared.append(previewRecipient, previewLines, payload);
  section.append(heading, error, notice, periodReport, auto, autoApplied, empty, examples, conversation, proposed, requestField, actions, pending, warnings, disclosure, prepared);
  root.replaceChildren(section);
  // The elapsed seconds belong to a running turn, so the panel owns the timer that reads them.
  let turnTimer: ReturnType<typeof globalThis.setInterval> | null = null;
  const stopTurnTimer = (): void => { if (turnTimer !== null) globalThis.clearInterval(turnTimer); turnTimer = null; };
  const render = (): void => {
    error.hidden = !controller.error; error.textContent = controller.error;
    // After a batch the summary is the batch region's own line, and a period run says its own, so
    // the panel never says the same thing twice.
    notice.hidden = !controller.notice || controller.notice === controller.autoBatch?.notice || controller.notice === controller.period?.notice;
    notice.textContent = controller.notice;
    // S15: the report of the last period change, with the tracks it could not replace.
    const report = controller.period;
    periodReport.hidden = !report;
    periodNotice.textContent = report?.notice ?? '';
    const kept = report?.kept ?? [];
    periodKeptHeading.hidden = kept.length === 0;
    periodKeptHeading.textContent = kept.length > 0 ? listChatPeriodKept(kept.length) : '';
    periodKeptList.replaceChildren(...kept.map((line) => make('li', line)));
    autoToggle.checked = controller.autoApply;
    autoApplied.hidden = !controller.autoBatch;
    autoNotice.textContent = controller.autoBatch?.notice ?? '';
    autoList.replaceChildren(...(controller.autoBatch?.texts ?? []).map((line) => make('li', line)));
    // The undo belongs to that one batch: without one it is gone, not merely disabled.
    undoBatch.hidden = !controller.autoBatch;
    undoBatch.disabled = !controller.canUndoBatch;
    const busy = controller.pending !== null;
    const streaming = controller.pending === 'send';
    empty.hidden = controller.messages.length > 0 || streaming;
    examples.hidden = empty.hidden;
    conversation.replaceChildren(...controller.messages.map((message, index) => {
      const turn = make('li', '', `list-chat-turn list-chat-${message.role}`);
      // The announcement belongs to the reply it describes, so it is the first text of that turn.
      if (controller.readAgain === index) turn.append(make('p', LIST_CHAT_READ_AGAIN, 'review-notice list-chat-read-again'));
      turn.append(make('p', roleName[message.role], 'list-chat-role'), make('p', message.text, 'list-chat-text'));
      return turn;
    }));
    request.disabled = !controller.requestEditable;
    if (request.value !== controller.request) request.value = controller.request;
    send.disabled = !controller.canSend; reset.disabled = !controller.canReset;
    // S1: Cancelar exists only for a running turn; while it is ending it says so instead.
    cancel.hidden = !controller.canCancelTurn;
    cancel.disabled = !controller.canCancelTurn;
    cancel.textContent = controller.cancelling ? 'Cancelando…' : 'Cancelar';
    proposed.hidden = controller.actions.length === 0 && controller.droppedActions === 0;
    proposedCards.replaceChildren(...controller.actions.map((item, index) => {
      const card = make('li', '', 'list-chat-action');
      card.append(make('p', listChatActionText(item), 'list-chat-action-title'), make('p', item.reason, 'field-hint'));
      const apply = identify(make('button', 'Aplicar', 'button primary'), `apply-${index}`); apply.type = 'button';
      apply.disabled = !controller.applyEnabled;
      apply.setAttribute('aria-label', `Aplicar: ${listChatActionText(item)}`);
      apply.addEventListener('click', () => { if (!apply.disabled) void controller.apply(item.actionId); });
      card.append(apply); return card;
    }));
    dropped.hidden = controller.droppedActions <= 0;
    dropped.textContent = controller.droppedActions > 0 ? listChatDropped(controller.droppedActions) : '';
    // S2: the batch action only exists while two or more changes are still proposed.
    applyAll.hidden = controller.actions.length < 2;
    applyAll.disabled = !controller.canApplyAll;
    pending.hidden = !busy; pending.textContent = controller.pendingText;
    // S1: while a turn runs the line names its phase and how long it has taken, and a timer
    // redraws it every second; without a turn there is nothing to count and no timer to keep.
    const seconds = controller.elapsedSeconds(Date.now());
    const phase = controller.phaseText;
    pending.textContent = phase === '' ? controller.pendingText : `${phase} · ${seconds ?? 0} s`;
    if (seconds !== null) { if (turnTimer === null) turnTimer = globalThis.setInterval(render, 1000); }
    else stopTurnTimer();
    // S3: the host's notes are drawn as text, never as markup, and never claim a change.
    warnings.hidden = controller.warnings.length === 0;
    warnings.replaceChildren(...controller.warnings.map((line) => make('li', line)));
    prepared.hidden = !controller.preview;
    previewLines.replaceChildren();
    if (controller.preview) for (const line of controller.preview.disclosure) previewLines.append(make('li', line));
    payload.hidden = !controller.preview;
    payloadSummary.setAttribute('aria-disabled', String(busy || !controller.preview));
    payloadBody.textContent = controller.payload ? controller.payload.body : '';
    payloadHint.textContent = `${controller.payload?.truncated ? 'El cuerpo supera el límite y se muestra truncado. ' : ''}Solo lectura local del cuerpo exacto que se enviaría al proveedor. Abrirlo no envía nada.`;
  };
  render();
  return render;
}
