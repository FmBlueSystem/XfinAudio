import { AI_RECIPIENT } from './optional-ai.js';
import { LIST_CHAT_PROPOSED, LIST_CHAT_READ_AGAIN, listChatActionText, listChatDropped } from './list-chat.js';
import type { ListChatController } from './list-chat.js';
/** S7's exact copy: the empty state and the three questions that only fill the box. */
export const LIST_CHAT_EMPTY = 'Pregunta cómo mejorar esta lista. El asistente lee las pistas, las transiciones y los avisos.';
export const LIST_CHAT_EXAMPLES = ['¿Qué transiciones son las más débiles?', '¿Qué pista quitarías y por qué?', '¿Cómo mejoro la curva de energía?'] as const;
export const LIST_CHAT_DISCLOSURE = 'El asistente lee la lista y la conversación con Nan Builders: se comparten los títulos, artistas y metadatos de la lista, sus transiciones, la preparación y los avisos; nunca rutas de archivo ni identificadores de pista. La lista solo se lee: el asistente no la cambia.';
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
export function createListChatView(root: HTMLElement, controller: ListChatController, options: { idPrefix?: string } = {}): () => void {
  const prefix = options.idPrefix ?? 'list-chat';
  const identify = <T extends HTMLElement>(node: T, suffix: string): T => { node.id = `${prefix}-${suffix}`; return node; };
  const section = make('section', '', 'surface prep-form list-chat'); section.setAttribute('aria-labelledby', `${prefix}-heading`);
  const heading = identify(make('h3', 'Asistente de lista'), 'heading');
  const error = identify(make('p', '', 'review-notice blocker'), 'error'); error.setAttribute('role', 'alert');
  const notice = identify(make('p', '', 'review-notice'), 'notice'); notice.setAttribute('role', 'status');
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
  actions.append(send, reset);
  const pending = identify(make('p', '', 'review-notice'), 'pending'); pending.setAttribute('role', 'status');
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
  section.append(heading, error, notice, empty, examples, conversation, proposed, requestField, actions, pending, disclosure, prepared);
  root.replaceChildren(section);
  const render = (): void => {
    error.hidden = !controller.error; error.textContent = controller.error;
    notice.hidden = !controller.notice; notice.textContent = controller.notice;
    const busy = controller.pending !== null;
    const streaming = controller.pending === 'send';
    empty.hidden = controller.messages.length > 0 || streaming;
    examples.hidden = !empty.hidden;
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
