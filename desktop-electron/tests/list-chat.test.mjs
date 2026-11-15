import assert from 'node:assert/strict';
import test from 'node:test';
import { ListChatController, CHAT_SURFACE, LIST_CHAT_PENDING } from '../.out/renderer/list-chat.js';
const uuid = '12345678-1234-4123-8123-123456789012';
const uuid2 = '87654321-4321-4321-8321-210987654321';
const question = '¿Qué pista quitarías y por qué?';
const reply = 'Quitaría la segunda pista: comparte tonalidad y baja la energía.';
const conversation = (...items) => items.reduce((list, text, index) => [...list, { role: index % 2 === 0 ? 'user' : 'assistant', text }], []);
const preview = (input) => ({ previewId: uuid, surface: CHAT_SURFACE, recipient: 'https://api.nan.builders/v1/chat/completions', disclosure: ['Se comparten títulos, artistas y transiciones, nunca rutas.'], requestPreview: input.request, firstTurn: true });
const chatResult = (patch = {}) => ({ resultId: uuid, surface: CHAT_SURFACE, kind: 'chat', title: 'Asistente de lista', text: reply, proposal: null, canApply: false, conversation: conversation(question, reply), listChanged: false, ...patch });
const retained = { previewId: uuid, surface: CHAT_SURFACE, recipient: 'https://api.nan.builders/v1/chat/completions', request: question, body: '{"model":"deepseek","messages":[]}', bytes: 31, truncated: false };
function fixture(overrides = {}) {
  const calls = []; let allowed = true; let renders = 0;
  const base = {
    aiChatHistory: async () => { calls.push(['history']); return { conversation: conversation('Pregunta previa', 'Respuesta previa') }; },
    aiChatReset: async () => { calls.push(['reset']); return { conversation: [] }; },
    prepareAiRequest: async (input) => { calls.push(['prepare', input]); return preview(input); },
    runAiRequest: async (input) => { calls.push(['run', input]); return { cancelled: false, result: chatResult() }; },
    inspectAiPayload: async (input) => { calls.push(['payload', input]); return retained; },
  };
  const api = { ...base, ...overrides };
  const controller = new ListChatController(api, { canAct: () => allowed, changed: () => { renders++; }, perform: async (_label, task, apply, fail) => { try { apply(await task(), true); } catch (error) { fail(error); } } });
  controller.setReview(uuid);
  return { controller, calls, renders: () => renders, block: () => { allowed = false; } };
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
test('a new conversation calls aiChatReset and empties the transcript', async () => {
  const f = fixture();
  await f.controller.load();
  f.controller.setRequest(question);
  await f.controller.newConversation();
  assert.deepEqual(f.calls.at(-1), ['reset']);
  assert.deepEqual(f.controller.messages, []);
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
test('the pending copy names the read while a turn runs', () => {
  const f = fixture();
  f.controller.pending = 'send';
  assert.equal(f.controller.pendingText, LIST_CHAT_PENDING);
  assert.equal(LIST_CHAT_PENDING, 'El asistente está leyendo la lista…');
  assert.equal(f.controller.canSend, false);
  assert.equal(f.controller.requestEditable, false);
});
