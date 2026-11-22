import assert from 'node:assert/strict';
import test from 'node:test';
import { ListChatController, CHAT_SURFACE, LIST_CHAT_PENDING, listChatActionText, listChatAppliedAll, listChatAutoApplied, listChatBatchUndone } from '../.out/renderer/list-chat.js';
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
const extendAction = (patch = {}) => ({ actionId: uuid, type: 'extend', to: 20, reason: 'La lista se quedó en cuatro pistas', ...patch });
const variantAction = (patch = {}) => ({ actionId: uuid2, type: 'use_variant', variant: 'adventurous', trackCount: 20, reason: 'La exploratoria entra sin perder el orden', ...patch });
const appliedReview = { reviewId: uuid2, tracks: [{ id: 'a'.repeat(64), title: 'Reemplazo', artist: 'DJ Cuatro', bpm: 124, key: '9A', energy: 6, duration: 200 }], warnings: [], blockers: [], name: 'Sesión', variant: 'balanced', readiness: 'ready' };
function fixture(overrides = {}, hostOverrides = {}) {
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
  const controller = new ListChatController(api, { canAct: () => allowed, changed: () => { renders++; }, applied: (value) => { applied.push(value); }, perform: async (_label, task, apply, fail) => { try { apply(await task(), true); } catch (error) { fail(error); } }, ...hostOverrides });
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
  f.controller.setAutoApply(false);
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
  f.controller.setAutoApply(false);
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
    chatResult({ actions: manyOf(21, (index) => moveAction({ actionId: idOf(index), position: index, to: index + 1 })) }),
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
  f.controller.setAutoApply(false);
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
  f.controller.setAutoApply(false);
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
  f.controller.setAutoApply(false);
  f.controller.setRequest(question);
  await f.controller.send();
  await f.controller.apply(uuid2);
  assert.equal(f.controller.error, 'Revisa los datos de la operación y sus límites antes de intentarlo de nuevo.');
  assert.deepEqual(f.controller.actions, [moveAction()]);
  assert.equal(f.applied.length, 0);
});
test('an apply is refused while anything runs or when the action is unknown', async () => {
  const blocked = fixture({ runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [moveAction()] }) }) });
  blocked.controller.setAutoApply(false);
  blocked.controller.setRequest(question);
  await blocked.controller.send();
  blocked.block();
  assert.equal(blocked.controller.applyEnabled, false);
  await blocked.controller.apply(uuid2);
  const unknown = fixture({ runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [moveAction()] }) }) });
  unknown.controller.setAutoApply(false);
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
test('S6 copy: an extend card names its target and a variant card names the alternative and its count', () => {
  assert.equal(listChatActionText(extendAction()), 'Ampliar la lista a 20 pistas');
  assert.equal(listChatActionText(variantAction()), 'Usar la alternativa exploratoria (20 pistas)');
  assert.equal(listChatActionText(variantAction({ variant: 'safe', trackCount: 4 })), 'Usar la alternativa segura (4 pistas)');
  assert.equal(listChatActionText(variantAction({ variant: 'balanced', trackCount: 17 })), 'Usar la alternativa equilibrada (17 pistas)');
  assert.equal(listChatActionText(moveAction()), 'Mover 3. Tercera a la posición 1', 'the two older shapes keep their text');
  assert.equal(listChatActionText(replaceAction()), 'Reemplazar 2. Segunda por Reemplazo');
});
test('the two new proposal shapes are accepted from history and from a reply', async () => {
  const stored = fixture({ aiChatHistory: async () => { stored.calls.push(['history']); return { conversation: conversation('Pregunta previa', 'Respuesta previa'), actions: [extendAction(), variantAction()] }; } });
  await stored.controller.load();
  assert.deepEqual(stored.controller.actions, [extendAction(), variantAction()]);
  const replied = fixture({ runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [extendAction(), variantAction()] }) }) });
  replied.controller.setAutoApply(false);
  replied.controller.setRequest(question);
  await replied.controller.send();
  assert.deepEqual(replied.controller.actions, [extendAction(), variantAction()]);
  assert.equal(replied.controller.error, '');
});
test('an extend or use_variant card that is not exactly its shape is refused as an invalid AI response', async () => {
  const malformed = [
    chatResult({ actions: [extendAction({ title: 'Segunda' })] }),
    chatResult({ actions: [extendAction({ position: 2 })] }),
    chatResult({ actions: [extendAction({ to: 101 })] }),
    chatResult({ actions: [extendAction({ to: 1 })] }),
    chatResult({ actions: [extendAction({ to: 1.5 })] }),
    chatResult({ actions: [extendAction({ to: '20' })] }),
    chatResult({ actions: [extendAction({ type: 'extend ' })] }),
    chatResult({ actions: [variantAction({ variant: 'balanced ' })] }),
    chatResult({ actions: [variantAction({ variant: 'saved' })] }),
    chatResult({ actions: [variantAction({ trackCount: 0 })] }),
    chatResult({ actions: [variantAction({ trackCount: 2.5 })] }),
    chatResult({ actions: [variantAction({ trackCount: '20' })] }),
    chatResult({ actions: [variantAction({ to: 20 })] }),
    chatResult({ actions: [variantAction({ reason: 'x'.repeat(201) })] }),
  ];
  for (const result of malformed) {
    const f = fixture({ runAiRequest: async () => ({ cancelled: false, result }) });
    await f.controller.load();
    f.controller.setRequest(question);
    await f.controller.send();
    assert.equal(f.controller.error, 'La respuesta no cumple los límites esperados. No se ha aplicado ninguna propuesta.', JSON.stringify(result.actions[0]).slice(0, 90));
    assert.deepEqual(f.controller.actions, []);
  }
});
test('applying an extend card sends its action, adopts the review and shows the S3 result line', async () => {
  const f = fixture({
    aiChatHistory: async () => ({ conversation: conversation('Pregunta previa', 'Respuesta previa'), actions: [extendAction()] }),
    aiChatApply: async (input) => { f.calls.push(['apply', input]); return { review: appliedReview, actions: [], extended: { requested: 16, added: 16, outsideGenre: 6 } }; },
  });
  await f.controller.load();
  await f.controller.apply(uuid);
  assert.deepEqual(f.calls.at(-1), ['apply', { actionId: uuid }]);
  assert.equal(f.applied.length, 1);
  assert.equal(f.controller.reviewId, appliedReview.reviewId);
  assert.equal(f.controller.notice, 'Se agregaron 16 pistas. 6 son de otros géneros.');
  assert.equal(f.controller.error, '');
  assert.deepEqual(f.controller.actions, []);
});
test('an extension that stayed inside the genre says only how many tracks it added', async () => {
  const f = fixture({
    aiChatHistory: async () => ({ conversation: conversation('Pregunta previa', 'Respuesta previa'), actions: [extendAction()] }),
    aiChatApply: async () => ({ review: appliedReview, actions: [], extended: { requested: 16, added: 4, outsideGenre: 0 } }),
  });
  await f.controller.load();
  await f.controller.apply(uuid);
  assert.equal(f.controller.notice, 'Se agregaron 4 pistas.');
});
test('an extension the core cannot complete shows the S3 line and keeps its card', async () => {
  const f = fixture({
    aiChatHistory: async () => ({ conversation: conversation('Pregunta previa', 'Respuesta previa'), actions: [extendAction()] }),
    aiChatApply: async () => { throw Object.assign(new Error('nothing'), { code: 'no_candidates' }); },
  });
  await f.controller.load();
  await f.controller.apply(uuid);
  assert.equal(f.controller.notice, 'No hay más pistas que mezclen con esta lista.');
  assert.equal(f.controller.error, '');
  assert.deepEqual(f.controller.actions, [extendAction()]);
  assert.equal(f.applied.length, 0);
});
test('a malformed extended answer is refused and leaves the cards and the review alone', async () => {
  for (const extended of [{ requested: 16, added: 'x', outsideGenre: 0 }, { requested: 16, added: 4 }, { added: 4, outsideGenre: 0 }, { requested: 16, added: -1, outsideGenre: 0 }, null]) {
    const f = fixture({
      aiChatHistory: async () => ({ conversation: conversation('Pregunta previa', 'Respuesta previa'), actions: [extendAction()] }),
      aiChatApply: async () => ({ review: appliedReview, actions: [], extended }),
    });
    await f.controller.load();
    await f.controller.apply(uuid);
    assert.equal(f.controller.error, 'La respuesta no cumple los límites esperados. No se ha aplicado ninguna propuesta.', JSON.stringify(extended));
    assert.deepEqual(f.controller.actions, [extendAction()]);
    assert.equal(f.applied.length, 0);
    assert.equal(f.controller.reviewId, uuid);
  }
});
test('«Aplicar» on a use_variant card chooses that alternative and announces the new conversation', async () => {
  const chosen = [];
  const f = fixture(
    { aiChatHistory: async () => ({ conversation: conversation('Pregunta previa', 'Respuesta previa'), actions: [variantAction()] }) },
    { chooseVariant: async (variant) => { chosen.push(variant); f.controller.setReview(uuid2); return true; } },
  );
  await f.controller.load();
  await f.controller.apply(uuid2);
  assert.deepEqual(chosen, ['adventurous']);
  assert.equal(f.calls.some(([kind]) => kind === 'apply'), false, 'choosing an alternative never applies it in the core');
  assert.equal(f.controller.notice, 'Se cambió la alternativa. La conversación empieza de nuevo.');
  assert.equal(f.controller.error, '');
  assert.deepEqual(f.controller.messages, [], 'the new alternative starts a new conversation');
  assert.deepEqual(f.controller.actions, []);
  assert.equal(f.controller.reviewId, uuid2);
  assert.equal(f.controller.pending, null);
});
test('a declined discard question leaves the cards, the conversation and the review as they were', async () => {
  const chosen = [];
  const f = fixture(
    { aiChatHistory: async () => ({ conversation: conversation('Pregunta previa', 'Respuesta previa'), actions: [variantAction()] }) },
    { chooseVariant: async (variant) => { chosen.push(variant); return false; } },
  );
  await f.controller.load();
  await f.controller.apply(uuid2);
  assert.deepEqual(chosen, ['adventurous']);
  assert.equal(f.controller.notice, '');
  assert.equal(f.controller.error, '');
  assert.deepEqual(f.controller.actions, [variantAction()]);
  assert.deepEqual(f.controller.messages.map((item) => item.text), ['Pregunta previa', 'Respuesta previa']);
  assert.equal(f.controller.reviewId, uuid);
  assert.equal(f.controller.pending, null);
});
test('a use_variant card without the screen hook says the app must be updated and applies nothing', async () => {
  const f = fixture({ aiChatHistory: async () => ({ conversation: conversation('Pregunta previa', 'Respuesta previa'), actions: [variantAction()] }) });
  await f.controller.load();
  await f.controller.apply(uuid2);
  assert.equal(f.controller.error, 'Actualiza la aplicación para cambiar de alternativa desde el asistente.');
  assert.equal(f.calls.some(([kind]) => kind === 'apply'), false);
  assert.deepEqual(f.controller.actions, [variantAction()]);
});
// S5's five new shapes, exactly as the core shows them to the panel.
const actionUuid = (n) => `${String(n).repeat(8)}-1111-4111-8111-111111111111`;
/** A distinct action id per index, so a reply can carry the twenty changes S14 allows. */
const idOf = (n) => `${String(n).padStart(8, '0')}-1111-4111-8111-111111111111`;
const manyOf = (count, make) => Array.from({ length: count }, (_, index) => make(index + 1));
const removeAction = (patch = {}) => ({ actionId: actionUuid(1), type: 'remove', position: 2, title: 'Segunda', artist: 'DJ Dos', reason: 'Choca de tonalidad con la tercera', ...patch });
const addAction = (patch = {}) => ({ actionId: actionUuid(2), type: 'add', position: 3, track: { title: 'Nueva', artist: 'DJ Cinco', bpm: 126, key: '10A' }, reason: 'Sube la energía del cierre', ...patch });
const replaceWithAction = (patch = {}) => ({ actionId: actionUuid(3), type: 'replace_with', position: 2, title: 'Segunda', artist: 'DJ Dos', track: { title: 'Otra', artist: 'DJ Seis', bpm: 124, key: '9A' }, reason: 'Encaja mejor con la tercera', ...patch });
const reorderAction = (patch = {}) => ({ actionId: actionUuid(4), type: 'reorder', moved: 3, reason: 'La curva de energía sube antes', ...patch });
const undoAction = (patch = {}) => ({ actionId: actionUuid(5), type: 'undo', reason: 'El orden anterior era mejor', ...patch });
test('S6 copy: the five new cards say exactly what they do', () => {
  assert.equal(listChatActionText(removeAction()), 'Quitar 2. Segunda');
  assert.equal(listChatActionText(addAction()), 'Agregar Nueva en la posición 3');
  assert.equal(listChatActionText(replaceWithAction()), 'Reemplazar 2. Segunda por Otra');
  assert.equal(listChatActionText(reorderAction()), 'Reordenar la lista (3 pistas cambian de lugar)');
  assert.equal(listChatActionText(reorderAction({ moved: 1 })), 'Reordenar la lista (1 pistas cambian de lugar)');
  assert.equal(listChatActionText(undoAction()), 'Deshacer el último cambio');
});
test('the five new proposal shapes are accepted from history and from a reply', async () => {
  const stored = fixture({ aiChatHistory: async () => { stored.calls.push(['history']); return { conversation: conversation('Pregunta previa', 'Respuesta previa'), actions: [removeAction(), replaceWithAction()] }; } });
  await stored.controller.load();
  assert.deepEqual(stored.controller.actions, [removeAction(), replaceWithAction()]);
  assert.equal(stored.controller.error, '');
  const replied = fixture({ runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [removeAction(), addAction(), replaceWithAction(), reorderAction(), undoAction()] }) }) });
  replied.controller.setAutoApply(false);
  replied.controller.setRequest(question);
  await replied.controller.send();
  assert.deepEqual(replied.controller.actions, [removeAction(), addAction(), replaceWithAction(), reorderAction(), undoAction()]);
  assert.equal(replied.controller.error, '');
  assert.equal(replied.controller.droppedActions, 0);
});
test('a new card that is not exactly its shape is refused as an invalid AI response', async () => {
  const malformed = [
    chatResult({ actions: [{ ...removeAction(), path: '/Users/dj/track.mp3' }] }),
    chatResult({ actions: [{ ...removeAction(), position: 0 }] }),
    chatResult({ actions: [{ ...removeAction(), position: 1.5 }] }),
    chatResult({ actions: [{ ...removeAction(), track: { title: 'Nueva', artist: 'DJ', bpm: 120, key: '9A' } }] }),
    chatResult({ actions: [{ ...addAction(), position: 0 }] }),
    chatResult({ actions: [{ ...addAction(), track: { title: 'Nueva', artist: 'DJ', bpm: 120 } }] }),
    chatResult({ actions: [{ ...addAction(), track: { title: 'Nueva', artist: 'DJ', bpm: 120, key: '9A', id: 'b'.repeat(64) } }] }),
    chatResult({ actions: [{ ...addAction(), title: 'Nueva' }] }),
    chatResult({ actions: [{ ...replaceWithAction(), track: { title: 'Otra', artist: 'DJ', bpm: 120, key: '9A', path: '/tmp/a.mp3' } }] }),
    chatResult({ actions: [{ ...reorderAction(), moved: 0 }] }),
    chatResult({ actions: [{ ...reorderAction(), moved: 101 }] }),
    chatResult({ actions: [{ ...reorderAction(), moved: 2.5 }] }),
    chatResult({ actions: [{ ...reorderAction(), order: [2, 1] }] }),
    chatResult({ actions: [{ ...undoAction(), position: 2 }] }),
    chatResult({ actions: [{ ...undoAction(), type: 'undo ' }] }),
    chatResult({ actions: manyOf(21, (index) => undoAction({ actionId: idOf(index) })) }),
  ];
  for (const result of malformed) {
    const f = fixture({ runAiRequest: async () => ({ cancelled: false, result }) });
    await f.controller.load();
    f.controller.setRequest(question);
    await f.controller.send();
    assert.equal(f.controller.error, 'La respuesta no cumple los límites esperados. No se ha aplicado ninguna propuesta.', JSON.stringify(result.actions[0]).slice(0, 90));
    assert.deepEqual(f.controller.actions, []);
    assert.equal(f.controller.droppedActions, 0);
  }
});
test('S2: «Aplicar todo» appears with two changes and is refused with only one', async () => {
  const one = fixture({ aiChatHistory: async () => ({ conversation: conversation('Pregunta previa', 'Respuesta previa'), actions: [removeAction()] }) });
  await one.controller.load();
  assert.equal(one.controller.canApplyAll, false);
  const two = fixture({ aiChatHistory: async () => ({ conversation: conversation('Pregunta previa', 'Respuesta previa'), actions: [removeAction(), addAction()] }) });
  await two.controller.load();
  assert.equal(two.controller.canApplyAll, true);
  await one.controller.applyAll();
  assert.equal(one.calls.some(([kind]) => kind === 'apply'), false);
});
test('S2: «Aplicar todo» applies the changes one after another in the order shown and reports the count', async () => {
  const seen = [];
  const f = fixture({
    aiChatHistory: async () => ({ conversation: conversation('Pregunta previa', 'Respuesta previa'), actions: [removeAction(), addAction()] }),
    aiChatApply: async (input) => { seen.push(input.actionId); f.calls.push(['apply', input]); return { review: appliedReview, actions: [] }; },
  });
  await f.controller.load();
  await f.controller.applyAll();
  assert.deepEqual(seen, [removeAction().actionId, addAction().actionId], 'the shown order is kept');
  assert.equal(f.controller.notice, 'Se aplicaron 2 de 2 cambios.');
  assert.equal(f.controller.error, '');
  assert.equal(f.applied.length, 2);
  assert.deepEqual(f.controller.actions, []);
  assert.equal(f.controller.pending, null);
});
test('S2: «Aplicar todo» stops at the first failure and still says how many changes were applied', async () => {
  const seen = [];
  const f = fixture({
    aiChatHistory: async () => ({ conversation: conversation('Pregunta previa', 'Respuesta previa'), actions: [removeAction(), addAction(), undoAction()] }),
    aiChatApply: async (input) => {
      seen.push(input.actionId);
      if (input.actionId === addAction().actionId) throw Object.assign(new Error('bad'), { code: 'invalid_params' });
      return { review: appliedReview, actions: [addAction(), undoAction()] };
    },
  });
  await f.controller.load();
  await f.controller.applyAll();
  assert.deepEqual(seen, [removeAction().actionId, addAction().actionId], 'the batch stops at the first failure');
  assert.equal(f.controller.notice, 'Se aplicaron 1 de 3 cambios.');
  assert.equal(f.controller.error, 'Revisa los datos de la operación y sus límites antes de intentarlo de nuevo.');
  assert.equal(f.applied.length, 1);
});
test('S2: «Aplicar todo» stops before a proposed alternative, which belongs to the screen', async () => {
  const f = fixture({
    aiChatHistory: async () => ({ conversation: conversation('Pregunta previa', 'Respuesta previa'), actions: [removeAction(), variantAction()] }),
    aiChatApply: async (input) => { f.calls.push(['apply', input]); return { review: appliedReview, actions: [variantAction()] }; },
  });
  await f.controller.load();
  await f.controller.applyAll();
  assert.equal(f.calls.filter(([kind]) => kind === 'apply').length, 1);
  assert.equal(f.controller.notice, 'Se aplicaron 1 de 2 cambios.');
});
test('S2: «Aplicar todo» is refused while the app cannot act', async () => {
  const f = fixture({ aiChatHistory: async () => ({ conversation: conversation('Pregunta previa', 'Respuesta previa'), actions: [removeAction(), addAction()] }) });
  await f.controller.load();
  f.block();
  assert.equal(f.controller.canApplyAll, false);
  await f.controller.applyAll();
  assert.equal(f.calls.some(([kind]) => kind === 'apply'), false);
});
// --- S9: automatic apply with one batch undo ---
test('S9: automatic apply is on by default and switching it off keeps the reply as cards', async () => {
  const f = fixture({ runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [removeAction(), addAction()] }) }) });
  assert.equal(f.controller.autoApply, true, 'the switch is on by default');
  f.controller.setAutoApply(false);
  f.controller.setRequest(question);
  await f.controller.send();
  assert.deepEqual(f.controller.actions, [removeAction(), addAction()]);
  assert.equal(f.calls.some(([kind]) => kind === 'apply'), false);
  assert.equal(f.controller.canApplyAll, true);
});
test('S9: a batch survives its own hand-offs to the screen and any other edit retires its undo', async () => {
  const seen = []; const applied = []; const ref = {};
  const f = fixture({
    runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [removeAction(), addAction()] }) }),
    aiChatApply: async (input) => { seen.push(input.actionId); f.calls.push(['apply', input]); return { review: appliedReview, actions: input.actionId === removeAction().actionId ? [addAction()] : [] }; },
    reviewUndo: async () => appliedReview,
  }, { applied: (value) => { applied.push(value.reviewId); ref.controller.reviewReplaced(); } });
  ref.controller = f.controller;
  f.controller.setRequest(question);
  await f.controller.send();
  assert.deepEqual(seen, [removeAction().actionId, addAction().actionId]);
  assert.equal(applied.length, 2);
  assert.equal(f.controller.canUndoBatch, true, 'the batch hands its own reviews to the screen without retiring itself');
  assert.equal(f.controller.notice, 'Se aplicaron 2 cambios.');
  ref.controller.reviewReplaced();
  assert.equal(f.controller.canUndoBatch, false, 'a manual edit of the list retires the batch undo');
});
test('S9: the batch undo disappears after use and undoes one step per applied change', async () => {
  const undos = [];
  const f = fixture({
    runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [removeAction(), addAction()] }) }),
    aiChatApply: async (input) => { f.calls.push(['apply', input]); return { review: appliedReview, actions: input.actionId === removeAction().actionId ? [addAction()] : [] }; },
    reviewUndo: async (input) => { undos.push({ ...input }); return { ...appliedReview, reviewId: undos.length === 1 ? uuid : uuid2 }; },
  });
  f.controller.setRequest(question);
  await f.controller.send();
  assert.equal(f.controller.notice, 'Se aplicaron 2 cambios.');
  await f.controller.undoBatch();
  assert.equal(f.controller.notice, 'Se deshicieron 2 cambios.');
  assert.deepEqual(undos, [{ reviewId: uuid2 }, { reviewId: uuid }], 'one undo per step, each on the review the previous one minted');
  assert.equal(f.controller.canUndoBatch, false);
  assert.equal(f.controller.error, '');
  await f.controller.undoBatch();
  assert.equal(undos.length, 2, 'a second click changes nothing');
});
async function batchUndoNotice(actions, expected) {
  const undos = [];
  const f = fixture({
    runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions }) }),
    aiChatApply: async () => ({ review: appliedReview, actions: [] }),
    reviewUndo: async (input) => { undos.push({ ...input }); return appliedReview; },
  });
  f.controller.setRequest(question);
  await f.controller.send();
  await f.controller.undoBatch();
  assert.equal(f.controller.notice, expected);
  assert.equal(undos.length, actions.length);
  assert.equal(f.controller.canUndoBatch, false);
}
test('S18(d): a one-change batch undo says one change', async () => {
  await batchUndoNotice([removeAction({ actionId: idOf(1) })], 'Se deshizo 1 cambio.');
});
test('S18(d): a three-change batch undo says three changes', async () => {
  await batchUndoNotice([
    removeAction({ actionId: idOf(1) }),
    addAction({ actionId: idOf(2) }),
    reorderAction({ actionId: idOf(3) }),
  ], 'Se deshicieron 3 cambios.');
});
test('S7 copy: the batch notices speak in the singular for one change and keep the plural otherwise', () => {
  assert.equal(listChatAutoApplied(1), 'Se aplicó 1 cambio.');
  assert.equal(listChatBatchUndone(1), 'Se deshizo 1 cambio.');
  assert.equal(listChatAutoApplied(2), 'Se aplicaron 2 cambios.');
  assert.equal(listChatBatchUndone(2), 'Se deshicieron 2 cambios.');
  assert.equal(listChatAppliedAll(1, 3), 'Se aplicaron 1 de 3 cambios.');
});
test('S6: a saved list never shows a use_variant card, from a reply or from history, and a generated one still does', async () => {
  const stored = fixture({ aiChatHistory: async () => ({ conversation: conversation(question, reply), actions: [variantAction()] }) });
  stored.controller.setReview(uuid, true);
  await stored.controller.load();
  assert.deepEqual(stored.controller.actions, []);
  const replied = fixture({ runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [variantAction(), removeAction({ actionId: idOf(1) })] }) }) });
  replied.controller.setReview(uuid, true);
  replied.controller.setAutoApply(false);
  replied.controller.setRequest(question);
  await replied.controller.send();
  assert.deepEqual(replied.controller.actions.map((action) => action.type), ['remove'], 'only the alternative card is withheld');
  const generated = fixture({ runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [variantAction()] }) }) });
  generated.controller.setAutoApply(false);
  generated.controller.setRequest(question);
  await generated.controller.send();
  assert.deepEqual(generated.controller.actions, [variantAction()]);
});
// --- S15: fit the list to a period, card and report ---
const periodAction = (patch = {}) => ({ actionId: idOf(8), type: 'period', yearMin: 1980, yearMax: 1999, outside: 7, reason: 'El DJ pidió solo los 80 y los 90', ...patch });
const periodAnswer = (patch = {}) => ({ yearMin: 1980, yearMax: 1999, replaced: 3, kept: [{ position: 1, title: 'Apertura', year: 1975, reason: 'protected' }, { position: 6, title: 'Rareza', year: null, reason: 'no_candidate' }], ...patch });
test('S15 copy: the period card names the range and the unprotected tracks outside it', () => {
  assert.equal(listChatActionText(periodAction()), 'Ajustar la lista a 1980–1999 (7 pistas fuera de época)');
  assert.equal(listChatActionText(periodAction({ yearMin: 1990, yearMax: 1999, outside: 1 })), 'Ajustar la lista a 1990–1999 (1 pistas fuera de época)');
});
test('S15: the period shape is accepted from history and from a reply, and a reply may now carry twenty changes', async () => {
  const stored = fixture({ aiChatHistory: async () => { stored.calls.push(['history']); return { conversation: conversation('Pregunta previa', 'Respuesta previa'), actions: [periodAction()] }; } });
  await stored.controller.load();
  assert.deepEqual(stored.controller.actions, [periodAction()]);
  assert.equal(stored.controller.error, '');
  const twenty = manyOf(19, (index) => removeAction({ actionId: idOf(index + 9), position: index + 1 }));
  const replied = fixture({ runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [...twenty, periodAction({ actionId: idOf(40) })] }) }) });
  replied.controller.setAutoApply(false);
  replied.controller.setRequest(question);
  await replied.controller.send();
  assert.equal(replied.controller.error, '');
  assert.equal(replied.controller.actions.length, 20);
  assert.deepEqual(replied.controller.actions.at(-1), periodAction({ actionId: idOf(40) }));
});
test('a period card that is not exactly its shape is refused as an invalid AI response', async () => {
  const malformed = [
    periodAction({ path: '/Users/dj/track.mp3' }),
    periodAction({ position: 2 }),
    periodAction({ type: 'period ' }),
    periodAction({ yearMin: 1899 }),
    periodAction({ yearMax: 2101 }),
    periodAction({ yearMin: 2000, yearMax: 1990 }),
    periodAction({ yearMin: 1980.5 }),
    periodAction({ yearMax: '1999' }),
    periodAction({ outside: -1 }),
    periodAction({ outside: 1.5 }),
    periodAction({ outside: 101 }),
    periodAction({ outside: undefined }),
  ];
  for (const action of malformed) {
    const f = fixture({ runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [action] }) }) });
    await f.controller.load();
    f.controller.setRequest(question);
    await f.controller.send();
    assert.equal(f.controller.error, 'La respuesta no cumple los límites esperados. No se ha aplicado ninguna propuesta.', JSON.stringify(action).slice(0, 90));
    assert.deepEqual(f.controller.actions, []);
    assert.equal(f.controller.period, null);
  }
});
test('S15: applying the period card adopts the review and reports what was replaced and what stayed out', async () => {
  const f = fixture({
    aiChatHistory: async () => ({ conversation: conversation('Pregunta previa', 'Respuesta previa'), actions: [periodAction()] }),
    aiChatApply: async (input) => { f.calls.push(['apply', input]); return { review: appliedReview, actions: [], period: periodAnswer() }; },
  });
  await f.controller.load();
  await f.controller.apply(periodAction().actionId);
  assert.deepEqual(f.calls.at(-1), ['apply', { actionId: periodAction().actionId }]);
  assert.equal(f.applied.length, 1);
  assert.equal(f.controller.reviewId, appliedReview.reviewId);
  assert.equal(f.controller.error, '');
  assert.deepEqual(f.controller.actions, []);
  assert.deepEqual(f.controller.period, {
    notice: 'Se reemplazaron 3 pistas.',
    kept: ['1. Apertura (1975) — protegida', '6. Rareza (sin año) — no hay otra de esa época que mezcle'],
  });
});
test('S15: a period that replaced every track keeps the report to its one line', async () => {
  const f = fixture({
    aiChatHistory: async () => ({ conversation: conversation('Pregunta previa', 'Respuesta previa'), actions: [periodAction()] }),
    aiChatApply: async () => ({ review: appliedReview, actions: [], period: periodAnswer({ replaced: 20, kept: [] }) }),
  });
  await f.controller.load();
  await f.controller.apply(periodAction().actionId);
  assert.equal(f.controller.notice, 'Se reemplazaron 20 pistas.');
  assert.deepEqual(f.controller.period, { notice: 'Se reemplazaron 20 pistas.', kept: [] });
});
test('S15: a malformed period answer is refused and leaves the card and the review alone', async () => {
  const kept = { position: 1, title: 'Apertura', year: 1975, reason: 'protected' };
  const malformed = [
    { yearMin: 1980, yearMax: 1999, replaced: 3 },
    { yearMin: 1980, yearMax: 1999, replaced: 3, kept: [], extra: 1 },
    { yearMin: 1980, yearMax: 1999, replaced: -1, kept: [] },
    { yearMin: 1980, yearMax: 1999, replaced: 3, kept: [{ ...kept, year: '1975' }] },
    { yearMin: 1980, yearMax: 1999, replaced: 3, kept: [{ ...kept, reason: 'other' }] },
    { yearMin: 1980, yearMax: 1999, replaced: 3, kept: [{ ...kept, title: '' }] },
    { yearMin: 1980, yearMax: 1999, replaced: 3, kept: [{ ...kept, position: 0 }] },
    { yearMin: 1980, yearMax: 1999, replaced: 3, kept: [{ ...kept, path: '/tmp/a.mp3' }] },
    null,
  ];
  for (const period of malformed) {
    const f = fixture({
      aiChatHistory: async () => ({ conversation: conversation('Pregunta previa', 'Respuesta previa'), actions: [periodAction()] }),
      aiChatApply: async () => ({ review: appliedReview, actions: [], period }),
    });
    await f.controller.load();
    await f.controller.apply(periodAction().actionId);
    assert.equal(f.controller.error, 'La respuesta no cumple los límites esperados. No se ha aplicado ninguna propuesta.', JSON.stringify(period).slice(0, 90));
    assert.deepEqual(f.controller.actions, [periodAction()]);
    assert.equal(f.applied.length, 0);
    assert.equal(f.controller.reviewId, uuid);
    assert.equal(f.controller.period, null);
  }
});
test('S15: a period change is applied automatically like the others and its report survives the batch', async () => {
  const f = fixture({
    runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [periodAction(), removeAction()] }) }),
    aiChatApply: async (input) => {
      f.calls.push(['apply', input]);
      return { review: appliedReview, actions: [], ...(input.actionId === periodAction().actionId ? { period: periodAnswer({ replaced: 4, kept: [{ position: 1, title: 'Apertura', year: 1975, reason: 'protected' }] }) } : {}) };
    },
  });
  f.controller.setRequest(question);
  await f.controller.send();
  assert.deepEqual(f.calls.filter(([kind]) => kind === 'apply').map(([, input]) => input.actionId), [periodAction().actionId, removeAction().actionId]);
  assert.equal(f.controller.notice, 'Se aplicaron 2 cambios.');
  assert.equal(f.controller.canUndoBatch, true);
  assert.deepEqual(f.controller.period, { notice: 'Se reemplazaron 4 pistas.', kept: ['1. Apertura (1975) — protegida'] });
});
test('S15: a new conversation or another review retires the period report', async () => {
  const f = fixture({
    aiChatHistory: async () => ({ conversation: conversation('Pregunta previa', 'Respuesta previa'), actions: [periodAction()] }),
    aiChatApply: async () => ({ review: appliedReview, actions: [], period: periodAnswer() }),
  });
  await f.controller.load();
  await f.controller.apply(periodAction().actionId);
  assert.ok(f.controller.period);
  await f.controller.newConversation();
  assert.equal(f.controller.period, null);
});
/** A turn whose prepare and provider call each stay open until the test releases them. */
function openTurn(overrides = {}, hostOverrides = {}) {
  const calls = []; const cancelled = []; const gate = {};
  const api = {
    aiChatHistory: async () => { calls.push(['history']); return { conversation: [], actions: [] }; },
    aiChatReset: async () => { calls.push(['reset']); return { conversation: [], actions: [] }; },
    prepareAiRequest: (input) => { calls.push(['prepare', input]); return new Promise((resolve) => { gate.prepare = () => resolve(preview(input)); }); },
    runAiRequest: (input) => { calls.push(['run', input]); return new Promise((resolve) => { gate.run = (value = { cancelled: false, result: chatResult() }) => resolve(value); }); },
    inspectAiPayload: async () => retained,
    aiChatApply: async () => { throw new Error('unreachable'); },
    ...overrides,
  };
  const controller = new ListChatController(api, {
    canAct: () => true, changed: () => {},
    perform: async (_label, task, apply, fail) => { try { apply(await task(), true); } catch (error) { fail(error); } },
    cancel: () => cancelled.push('cancel'), ...hostOverrides,
  });
  controller.setReview(uuid);
  const tick = () => new Promise((resolve) => setImmediate(resolve));
  return { controller, calls, cancelled, gate, tick };
}
test('S1: a running turn names its phase and how long it has been running', async () => {
  const realNow = Date.now; let clock = 1000; Date.now = () => clock;
  const f = openTurn();
  try {
    f.controller.setRequest(question);
    const turn = f.controller.send();
    await f.tick();
    assert.equal(f.controller.pending, 'send');
    assert.equal(f.controller.phase, 'preparing');
    assert.equal(f.controller.phaseText, 'Preparando la solicitud…');
    assert.equal(f.controller.elapsedSeconds(1000), 0);
    clock = 5400;
    assert.equal(f.controller.elapsedSeconds(5400), 4, 'the panel counts whole seconds it has been waiting');
    assert.equal(f.controller.canCancelTurn, true);
    f.gate.prepare();
    await f.tick();
    assert.equal(f.controller.phase, 'confirming');
    assert.equal(f.controller.phaseText, 'Esperando el diálogo de confirmación del sistema…');
    f.controller.askStarted();
    assert.equal(f.controller.phase, 'waiting');
    assert.equal(f.controller.phaseText, 'Esperando la respuesta de la IA…');
    f.gate.run();
    await turn;
    assert.equal(f.controller.phase, null);
    assert.equal(f.controller.elapsedSeconds(clock), null);
    assert.equal(f.controller.canCancelTurn, false);
    assert.deepEqual(f.calls.filter(([kind]) => kind === 'run'), [['run', { previewId: uuid }]]);
  } finally { Date.now = realNow; }
});
test('S1: cancelling ends the turn, says so in Spanish and ignores the answer that arrives later', async () => {
  const f = openTurn();
  f.controller.setRequest(question);
  const turn = f.controller.send();
  await f.tick();
  assert.equal(f.controller.notice, '');
  f.gate.prepare();
  await f.tick();
  f.gate.run();
  f.controller.askStarted();
  assert.equal(f.controller.phase, 'waiting');
  f.controller.cancel();
  assert.deepEqual(f.cancelled, ['cancel'], 'the app is asked to stop the turn');
  assert.equal(f.controller.cancelling, true);
  assert.equal(f.controller.pendingText, 'Cancelando la consulta…');
  assert.equal(f.controller.canCancelTurn, false);
  assert.equal(f.controller.notice, 'Consulta cancelada. La lista no cambió.');
  assert.equal(f.controller.phase, null);
  // The provider answers the turn nobody waits for any more: it is ignored.
  f.gate.run();
  await turn;
  assert.deepEqual(f.controller.messages, [], 'nothing is appended after a cancelled turn');
  assert.deepEqual(f.controller.actions, [], 'the list stays untouched');
  assert.equal(f.controller.notice, 'Consulta cancelada. La lista no cambió.');
  assert.equal(f.controller.error, '');
  assert.equal(f.controller.pending, null);
  assert.equal(f.controller.cancelling, false);
  assert.equal(f.controller.request, question, 'the question stays in the box for a retry');
});
test('S1: cancelling before the provider is contacted never contacts it', async () => {
  const f = openTurn();
  f.controller.setRequest(question);
  const turn = f.controller.send();
  await f.tick();
  f.controller.cancel();
  f.gate.prepare();
  await turn;
  assert.deepEqual(f.calls.map(([kind]) => kind), ['prepare'], 'a cancelled turn sends nothing');
  assert.deepEqual(f.controller.messages, []);
  assert.equal(f.controller.notice, 'Consulta cancelada. La lista no cambió.');
});
test('S3: an automatic batch that applied nothing says so instead of staying silent', async () => {
  const f = fixture({
    runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [moveAction()] }) }),
    aiChatApply: async () => { throw Object.assign(new Error('[stale_ai] stale'), { code: 'stale_ai' }); },
  });
  f.controller.setRequest(question);
  await f.controller.send();
  assert.equal(f.controller.autoApply, true);
  assert.equal(f.controller.notice, 'No se aplicó ningún cambio de esta respuesta.');
});
test('S3: a reply that only proposes the screen-owned alternative says nothing was applied, because nothing was', async () => {
  const f = fixture({ runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [variantAction()] }) }) });
  f.controller.setRequest(question);
  await f.controller.send();
  assert.equal(f.controller.notice, '', 'the card itself says the change is still pending');
  assert.equal(f.controller.actions.length, 1, 'the alternative stays as a card');
});
test('S3: an apply the panel refuses says why in the chat', async () => {
  const stored = { aiChatHistory: async () => ({ conversation: conversation(question, reply), actions: [moveAction()] }) };
  const f = fixture(stored);
  await f.controller.load();
  f.block();
  await f.controller.apply(moveAction().actionId);
  assert.equal(f.controller.notice, 'No se aplicó: espera a que termine la operación en curso.');
  const g = fixture(stored);
  await g.controller.load();
  await g.controller.apply(uuid);
  assert.equal(g.controller.notice, 'Ese cambio ya no está disponible: la última respuesta lo reemplazó.');
  assert.deepEqual(g.controller.actions, [moveAction()], 'the cards stay as they were');
});
test('S2: a provider call that expired says so in Spanish and keeps the question', async () => {
  const f = fixture({ runAiRequest: async () => { throw Object.assign(new Error('[ai_timeout] timed out'), { code: 'ai_timeout' }); } });
  f.controller.setRequest(question);
  await f.controller.send();
  assert.equal(f.controller.error, 'El proveedor no respondió a tiempo. La consulta terminó sin cambios en la lista; puedes reintentarla.');
  assert.equal(f.controller.request, question, 'the question stays for a retry');
  assert.deepEqual(f.controller.messages, []);
});
test('S3: what the system could not store is shown beside the answer in Spanish', async () => {
  const f = fixture({ runAiRequest: async () => ({ cancelled: false, result: chatResult(), notes: ['dialog_preference_not_saved', 'auto_authorize_unavailable'] }) });
  f.controller.setRequest(question);
  await f.controller.send();
  assert.deepEqual(f.controller.warnings, [
    'No se pudo guardar «No volver a preguntar en cada consulta»; puedes activarlo en Ajustes.',
    'No se pudo comprobar la autorización automática; la app volverá a pedir confirmación.',
  ]);
  assert.equal(f.controller.notice, '');
});
test('S3: an answer the host marks with an unknown note appends nothing', async () => {
  const f = fixture({ runAiRequest: async () => ({ cancelled: false, result: chatResult(), notes: ['invented'] }) });
  f.controller.setRequest(question);
  await f.controller.send();
  assert.deepEqual(f.controller.warnings, []);
});
