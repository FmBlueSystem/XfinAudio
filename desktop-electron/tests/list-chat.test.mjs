import assert from 'node:assert/strict';
import test from 'node:test';
import { ListChatController, CHAT_SURFACE, LIST_CHAT_PENDING } from '../.out/renderer/list-chat.js';
const uuid = '12345678-1234-4123-8123-123456789012';
const uuid2 = '87654321-4321-4321-8321-210987654321';
const question = '¿Qué pista quitarías y por qué?';
const reply = 'Quitaría la segunda pista: comparte tonalidad y baja la energía.';
const conversation = (...items) => items.reduce((list, text, index) => [...list, { role: index % 2 === 0 ? 'user' : 'assistant', text }], []);
const preview = (input) => ({ previewId: uuid, surface: CHAT_SURFACE, recipient: 'https://api.nan.builders/v1/chat/completions', disclosure: ['Se comparten títulos, artistas y transiciones, nunca rutas.'], requestPreview: input.request, firstTurn: true });
const chatResult = (patch = {}) => ({ resultId: uuid, surface: CHAT_SURFACE, kind: 'chat', title: 'Asistente de lista', text: reply, proposal: null, canApply: false, conversation: conversation(question, reply), listChanged: false, actions: [], droppedActions: 0, ...patch });
const retained = { previewId: uuid, surface: CHAT_SURFACE, recipient: 'https://api.nan.builders/v1/chat/completions', request: question, body: '{"model":"deepseek","messages":[]}', bytes: 31, truncated: false };
const moveAction = (patch = {}) => ({ actionId: uuid2, type: 'move', position: 3, to: 1, title: 'Tercera', artist: 'DJ Tres', reason: 'Sube la energía del inicio', ...patch });
const replaceAction = (patch = {}) => ({ actionId: uuid, type: 'replace', position: 2, title: 'Segunda', artist: 'DJ Dos', reason: 'Choca de tonalidad con la tercera', replacement: { title: 'Reemplazo', artist: 'DJ Cuatro', bpm: 124, key: '9A' }, ...patch });
const appliedReview = { reviewId: uuid2, tracks: [{ id: 'a'.repeat(64), title: 'Reemplazo', artist: 'DJ Cuatro', bpm: 124, key: '9A', energy: 6, duration: 200 }], warnings: [], blockers: [], name: 'Sesión', variant: 'balanced', readiness: 'ready' };
function fixture(overrides = {}) {
  const calls = []; const applied = []; let allowed = true; let renders = 0;
  const base = {
    aiChatHistory: async () => { calls.push(['history']); return { conversation: conversation('Pregunta previa', 'Respuesta previa'), actions: [] }; },
    aiChatReset: async () => { calls.push(['reset']); return { conversation: [], actions: [] }; },
    prepareAiRequest: async (input) => { calls.push(['prepare', input]); return preview(input); },
    runAiRequest: async (input) => { calls.push(['run', input]); return { cancelled: false, result: chatResult() }; },
    inspectAiPayload: async (input) => { calls.push(['payload', input]); return retained; },
    aiChatApply: async (input) => { calls.push(['apply', input]); throw new Error('unreachable'); },
  };
  const api = { ...base, ...overrides };
  const controller = new ListChatController(api, { canAct: () => allowed, changed: () => { renders++; }, applied: (value) => { applied.push(value); }, perform: async (_label, task, apply, fail) => { try { apply(await task(), true); } catch (error) { fail(error); } } });
  controller.setReview(uuid);
  return { controller, calls, applied, renders: () => renders, block: () => { allowed = false; } };
}
test('no turn is prepared or read before a review is published, and the panel cannot act while the app is busy', async () => {
  const f = fixture(); const fresh = new ListChatController({ aiChatHistory: async () => { throw new Error('unreachable'); }, aiChatReset: async () => { throw new Error('unreachable'); }, prepareAiRequest: async () => { throw new Error('unreachable'); }, runAiRequest: async () => { throw new Error('unreachable'); }, inspectAiPayload: async () => { throw new Error('unreachable'); } }, { canAct: () => true, changed: () => {}, perform: async () => {} });
  try {
    fresh.setRequest(question);
    assert.equal(fresh.canSend, false);
    await fresh.load(); await fresh.send(); await fresh.newConversation();
    f.block(); f.controller.setRequest(question);
    assert.equal(f.controller.canSend, false);
    await f.controller.send(); await f.controller.load();
    assert.deepEqual(f.calls, []);
  } finally { void f; }
});
test('opening the panel reads the stored conversation once', async () => {
  const f = fixture();
  assert.equal(f.controller.loaded, false);
  await f.controller.load();
  assert.deepEqual(f.controller.messages.map((item) => item.text), ['Pregunta previa', 'Respuesta previa']);
  assert.equal(f.controller.loaded, true);
  await f.controller.load();
  assert.deepEqual(f.calls, [['history']]);
});
test('a turn sends the exact chat selector and the typed question, then stores the conversation the core returns', async () => {
  const f = fixture();
  f.controller.setRequest(`  ${question}  `);
  assert.equal(f.controller.canSend, true);
  assert.equal(f.controller.requestEditable, true);
  await f.controller.send();
  assert.deepEqual(f.calls, [['prepare', { surface: 'chat', request: question, context: { reviewId: uuid } }], ['run', { previewId: uuid }]]);
  assert.deepEqual(f.controller.messages, conversation(question, reply));
  assert.equal(f.controller.request, '');
  assert.equal(f.controller.error, '');
  assert.equal(f.controller.readAgain, null);
  assert.equal(f.controller.pending, null);
  assert.ok(f.controller.preview);
});
test('a reply that re-read the list is marked so the panel can announce it before the reply', async () => {
  const f = fixture({ runAiRequest: async () => ({ cancelled: false, result: chatResult({ listChanged: true, conversation: conversation('Pregunta previa', 'Respuesta previa', question, reply) }) }) });
  f.controller.setRequest(question);
  await f.controller.send();
  assert.equal(f.controller.readAgain, 3);
  assert.equal(f.controller.messages[3].role, 'assistant');
});
test('a failed turn keeps the typed question in the box and shows the existing Spanish error text', async () => {
  const f = fixture({ runAiRequest: async (input) => { f.calls.push(['run', input]); throw Object.assign(new Error('provider down'), { code: 'ai_request_failed' }); } });
  await f.controller.load();
  f.controller.setRequest(question);
  await f.controller.send();
  assert.equal(f.controller.error, 'No se pudo completar la consulta al proveedor. Los datos ya enviados no se pueden recuperar.');
  assert.equal(f.controller.request, question);
  assert.deepEqual(f.controller.messages.map((item) => item.text), ['Pregunta previa', 'Respuesta previa']);
  assert.equal(f.controller.readAgain, null);
  assert.equal(f.controller.pending, null);
});
test('a malformed reply is refused as an invalid AI response and appends nothing', async () => {
  const malformed = [
    chatResult({ kind: 'commentary' }),
    chatResult({ text: '' }),
    chatResult({ text: 'x'.repeat(4001) }),
    chatResult({ proposal: { remove: [1] } }),
    chatResult({ canApply: true }),
    chatResult({ listChanged: undefined }),
    chatResult({ conversation: [{ role: 'system', text: 'no' }] }),
    chatResult({ conversation: [{ role: 'user', text: '' }] }),
    chatResult({ conversation: [{ role: 'assistant', text: 'ok', extra: true }] }),
  ];
  for (const result of malformed) {
    const f = fixture({ runAiRequest: async () => ({ cancelled: false, result }) });
    await f.controller.load();
    f.controller.setRequest(question);
    await f.controller.send();
    assert.equal(f.controller.error, 'La respuesta no cumple los límites esperados. No se ha aplicado ninguna propuesta.', JSON.stringify(result).slice(0, 80));
    assert.deepEqual(f.controller.messages.map((item) => item.text), ['Pregunta previa', 'Respuesta previa']);
    assert.equal(f.controller.request, question);
    assert.equal(f.controller.readAgain, null);
  }
});
test('a cancelled turn appends nothing and keeps the question for a retry', async () => {
  const f = fixture({ runAiRequest: async () => ({ cancelled: true, result: null }) });
  await f.controller.load();
  f.controller.setRequest(question);
  await f.controller.send();
  assert.equal(f.controller.error, '');
  assert.match(f.controller.notice, /cancelad/i);
  assert.equal(f.controller.request, question);
  assert.deepEqual(f.controller.messages.map((item) => item.text), ['Pregunta previa', 'Respuesta previa']);
});
test('a new conversation calls aiChatReset and empties the transcript and its proposed changes', async () => {
  const f = fixture({ runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [moveAction()] }) }) });
  f.controller.setRequest(question);
  await f.controller.send();
  assert.deepEqual(f.controller.actions, [moveAction()]);
  await f.controller.newConversation();
  assert.deepEqual(f.calls.at(-1), ['reset']);
  assert.deepEqual(f.controller.messages, []);
  assert.deepEqual(f.controller.actions, []);
  assert.equal(f.controller.request, '');
  assert.equal(f.controller.readAgain, null);
  assert.equal(f.controller.canReset, true);
});
test('another review clears the transcript but keeps the typed question', async () => {
  const f = fixture();
  await f.controller.load();
  f.controller.setRequest(question);
  f.controller.setReview(uuid2);
  assert.equal(f.controller.reviewId, uuid2);
  assert.deepEqual(f.controller.messages, []);
  assert.equal(f.controller.loaded, false);
  assert.equal(f.controller.request, question);
  f.controller.setReview(null);
  assert.equal(f.controller.reviewId, '');
  assert.equal(f.controller.canSend, false);
});
test('the exact retained body of the chat turn is inspectable only after a prepare', async () => {
  const f = fixture();
  f.controller.setRequest(question);
  await f.controller.inspectPayload();
  assert.deepEqual(f.calls, []);
  await f.controller.send();
  await f.controller.inspectPayload();
  assert.deepEqual(f.calls.at(-1), ['payload', { previewId: uuid }]);
  assert.deepEqual(f.controller.payload, retained);
});
test('a retained body that does not match the current chat preview is refused', async () => {
  const f = fixture({ inspectAiPayload: async () => ({ ...retained, previewId: uuid2 }) });
  f.controller.setRequest(question);
  await f.controller.send();
  await f.controller.inspectPayload();
  assert.equal(f.controller.payload, null);
  assert.equal(f.controller.error, 'La respuesta no cumple los límites esperados. No se ha aplicado ninguna propuesta.');
});
test('a question over 2000 characters cannot be sent and says so', async () => {
  const f = fixture();
  f.controller.setRequest('x'.repeat(2001));
  assert.equal(f.controller.canSend, false);
  assert.equal(f.controller.error, 'La petición admite como máximo 2000 caracteres.');
  await f.controller.send();
  assert.deepEqual(f.calls, []);
});
test('opening the panel shows the pending actions the core still holds', async () => {
  const f = fixture({ aiChatHistory: async () => { f.calls.push(['history']); return { conversation: conversation('Pregunta previa', 'Respuesta previa'), actions: [replaceAction()] }; } });
  assert.equal(f.controller.applyEnabled, true);
  await f.controller.load();
  assert.deepEqual(f.controller.actions, [replaceAction()]);
  assert.equal(f.controller.droppedActions, 0);
  assert.equal(f.controller.applyEnabled, true);
});
test('a turn keeps the proposed actions and counts the ones the core dropped', async () => {
  const f = fixture({ runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [replaceAction(), moveAction()], droppedActions: 2 }) }) });
  f.controller.setRequest(question);
  await f.controller.send();
  assert.deepEqual(f.controller.actions, [replaceAction(), moveAction()]);
  assert.equal(f.controller.droppedActions, 2);
});
test('a proposed action that is not exactly one of the two shapes is refused as an invalid AI response', async () => {
  const malformed = [
    chatResult({ actions: [{ ...moveAction(), path: '/Users/dj/track.mp3' }] }),
    chatResult({ actions: [{ ...moveAction(), position: 0 }] }),
    chatResult({ actions: [{ ...moveAction(), position: 2, to: 2 }] }),
    chatResult({ actions: [{ ...moveAction(), reason: 'x'.repeat(201) }] }),
    chatResult({ actions: [{ ...replaceAction(), replacement: { title: 'Uno', artist: 'DJ', bpm: 124 } }] }),
    chatResult({ actions: [{ ...replaceAction(), replacement: { title: 'Uno', artist: 'DJ', bpm: 124, key: '9A', id: 'b'.repeat(64) } }] }),
    chatResult({ actions: [{ ...moveAction(), type: 'remove' }] }),
    chatResult({ actions: [{ ...moveAction(), actionId: 'not-a-uuid' }] }),
    chatResult({ actions: [moveAction(), moveAction()] }),
    chatResult({ actions: [moveAction(), replaceAction(), moveAction(), replaceAction(), moveAction(), replaceAction()] }),
    chatResult({ droppedActions: -1 }),
    chatResult({ droppedActions: 1.5 }),
    chatResult({ actions: undefined }),
  ];
  for (const result of malformed) {
    const f = fixture({ runAiRequest: async () => ({ cancelled: false, result }) });
    await f.controller.load();
    f.controller.setRequest(question);
    await f.controller.send();
    assert.equal(f.controller.error, 'La respuesta no cumple los límites esperados. No se ha aplicado ninguna propuesta.');
    assert.deepEqual(f.controller.actions, []);
    assert.equal(f.controller.droppedActions, 0);
    assert.equal(f.controller.request, question);
    assert.deepEqual(f.controller.messages.map((item) => item.text), ['Pregunta previa', 'Respuesta previa']);
  }
});
test('Aplicar sends the action id, shows the returned review and keeps the remaining cards', async () => {
  const remaining = moveAction({ position: 1, to: 2 });
  const f = fixture({
    runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [replaceAction(), moveAction()] }) }),
    aiChatApply: async (input) => { f.calls.push(['apply', input]); return { review: appliedReview, actions: [remaining] }; },
  });
  f.controller.setRequest(question);
  await f.controller.send();
  await f.controller.apply(uuid);
  assert.deepEqual(f.calls.at(-1), ['apply', { actionId: uuid }]);
  assert.equal(f.applied.length, 1);
  assert.equal(f.applied[0].reviewId, uuid2);
  assert.equal(f.applied[0].tracks[0].title, 'Reemplazo');
  assert.equal(f.controller.reviewId, uuid2);
  assert.deepEqual(f.controller.actions, [remaining]);
  assert.equal(f.controller.notice, 'Cambio aplicado. Puedes deshacerlo con Deshacer.');
  assert.equal(f.controller.error, '');
  assert.deepEqual(f.controller.messages.map((item) => item.text), [question, reply]);
  // The app publishes the review the edit minted: this conversation and its cards stay.
  f.controller.setReview(uuid2);
  assert.deepEqual(f.controller.messages.map((item) => item.text), [question, reply]);
  assert.deepEqual(f.controller.actions, [remaining]);
});
test('a stale proposal shows the existing Spanish error text and removes the cards', async () => {
  const f = fixture({
    runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [moveAction()], droppedActions: 1 }) }),
    aiChatApply: async (input) => { f.calls.push(['apply', input]); throw Object.assign(new Error('gone'), { code: 'stale_ai' }); },
  });
  f.controller.setRequest(question);
  await f.controller.send();
  await f.controller.apply(uuid2);
  assert.equal(f.controller.error, 'El contexto o la solicitud cambió. Prepara otra vista previa y revisa de nuevo el consentimiento.');
  assert.deepEqual(f.controller.actions, []);
  assert.equal(f.controller.droppedActions, 0);
  assert.equal(f.applied.length, 0);
  assert.equal(f.controller.notice, '');
});
test('an apply that failed for another reason keeps the cards for a retry', async () => {
  const f = fixture({
    runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [moveAction()] }) }),
    aiChatApply: async () => { throw Object.assign(new Error('bad'), { code: 'invalid_params' }); },
  });
  f.controller.setRequest(question);
  await f.controller.send();
  await f.controller.apply(uuid2);
  assert.equal(f.controller.error, 'Revisa los datos de la operación y sus límites antes de intentarlo de nuevo.');
  assert.deepEqual(f.controller.actions, [moveAction()]);
  assert.equal(f.applied.length, 0);
});
test('an apply is refused while anything runs or when the action is unknown', async () => {
  const blocked = fixture({ runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [moveAction()] }) }) });
  blocked.controller.setRequest(question);
  await blocked.controller.send();
  blocked.block();
  assert.equal(blocked.controller.applyEnabled, false);
  await blocked.controller.apply(uuid2);
  const unknown = fixture({ runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [moveAction()] }) }) });
  unknown.controller.setRequest(question);
  await unknown.controller.send();
  await unknown.controller.apply(uuid);
  assert.equal(blocked.calls.some(([kind]) => kind === 'apply'), false);
  assert.equal(unknown.calls.some(([kind]) => kind === 'apply'), false);
});
test('the pending copy names the read while a turn runs', () => {
  const f = fixture();
  f.controller.pending = 'send';
  assert.equal(f.controller.pendingText, LIST_CHAT_PENDING);
  assert.equal(LIST_CHAT_PENDING, 'El asistente está leyendo la lista…');
  assert.equal(f.controller.canSend, false);
  assert.equal(f.controller.requestEditable, false);
});
