import assert from 'node:assert/strict';
import test from 'node:test';
import { ListChatController, CHAT_SURFACE } from '../.out/renderer/list-chat.js';
import { createListChatView } from '../.out/renderer/list-chat-view.js';
class Element extends EventTarget {
  constructor(tag = 'div') { super(); this.tagName = tag; }
  children = []; attrs = {}; textContent = ''; value = ''; checked = false; disabled = false; hidden = false;
  setAttribute(key, value) { this.attrs[key] = String(value); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  set innerHTML(_) { throw new Error('Unsafe HTML'); }
}
const all = (node) => [node, ...node.children.flatMap(all)];
const text = (node) => [node.textContent, ...node.children.map(text)].join(' ');
const uuid = '12345678-1234-4123-8123-123456789012';
const uuid2 = '87654321-4321-4321-8321-210987654321';
const question = '¿Qué transiciones son las más débiles?';
const reply = 'La transición 2→3 es la más débil: baja la energía y cambia de tonalidad.';
const empty = 'Pregunta cómo mejorar esta lista. El asistente lee las pistas, las transiciones y los avisos.';
const examples = ['¿Qué transiciones son las más débiles?', '¿Qué pista quitarías y por qué?', '¿Cómo mejoro la curva de energía?'];
const readAgain = 'El asistente volvió a leer la lista.';
const reading = 'El asistente está leyendo la lista…';
const providerError = 'No se pudo completar la consulta al proveedor. Los datos ya enviados no se pueden recuperar.';
const history = (...texts) => texts.reduce((list, value, index) => [...list, { role: index % 2 === 0 ? 'user' : 'assistant', text: value }], []);
const chatResult = (patch = {}) => ({ resultId: uuid, surface: CHAT_SURFACE, kind: 'chat', title: 'Asistente de lista', text: reply, proposal: null, canApply: false, conversation: history(question, reply), listChanged: false, actions: [], droppedActions: 0, ...patch });
const moveAction = (patch = {}) => ({ actionId: uuid2, type: 'move', position: 3, to: 1, title: 'Tercera', artist: 'DJ Tres', reason: 'Sube la energía del inicio', ...patch });
const replaceAction = (patch = {}) => ({ actionId: uuid, type: 'replace', position: 2, title: 'Segunda', artist: 'DJ Dos', reason: 'Choca de tonalidad con la tercera', replacement: { title: 'Reemplazo', artist: 'DJ Cuatro', bpm: 124, key: '9A' }, ...patch });
const appliedReview = { reviewId: uuid2, tracks: [{ id: 'a'.repeat(64), title: 'Reemplazo', artist: 'DJ Cuatro', bpm: 124, key: '9A', energy: 6, duration: 200 }], warnings: [], blockers: [], name: 'Sesión', variant: 'balanced', readiness: 'ready' };
const appliedNotice = 'Cambio aplicado. Puedes deshacerlo con Deshacer.';
const staleText = 'El contexto o la solicitud cambió. Prepara otra vista previa y revisa de nuevo el consentimiento.';
const tick = () => new Promise((resolve) => setImmediate(resolve));
async function fixture(overrides = {}, stored = ['¿Qué pista quitarías?', 'La segunda: comparte tonalidad con la tercera.'], storedActions = []) {
  const previous = globalThis.document; globalThis.document = { createElement: (tag) => new Element(tag) };
  const calls = []; const applied = []; let online = true; let render = () => {}; const root = new Element();
  const api = {
    aiChatHistory: async () => { calls.push(['history']); return { conversation: history(...stored), actions: storedActions.map((item) => ({ ...item })) }; },
    aiChatReset: async () => { calls.push(['reset']); return { conversation: [], actions: [] }; },
    prepareAiRequest: async (input) => { calls.push(['prepare', input]); return { previewId: uuid, surface: CHAT_SURFACE, recipient: 'https://api.nan.builders/v1/chat/completions', disclosure: ['Se comparten títulos, artistas y transiciones, nunca rutas de archivo.'], requestPreview: input.request, firstTurn: stored.length === 0 }; },
    runAiRequest: async (input) => { calls.push(['run', input]); return { cancelled: false, result: chatResult() }; },
    inspectAiPayload: async (input) => { calls.push(['payload', input]); return { previewId: uuid, surface: CHAT_SURFACE, recipient: 'https://api.nan.builders/v1/chat/completions', request: question, body: '{"model":"deepseek","messages":[]}', bytes: 31, truncated: false }; },
    aiChatApply: async (input) => { calls.push(['apply', input]); return { review: appliedReview, actions: [] }; },
    ...overrides,
  };
  const controller = new ListChatController(api, { canAct: () => online, changed: () => render(), applied: (value) => { applied.push(value); }, perform: async (_label, task, apply, fail) => { try { apply(await task(), true); } catch (error) { fail(error); } } });
  render = createListChatView(root, controller, { idPrefix: 'list-chat' });
  controller.setReview(uuid); await controller.load(); render();
  return { root, controller, calls, applied, render, get: (id) => all(root).find((node) => node.id === `list-chat-${id}`) ?? all(root).find((node) => node.id === `list-chat`), offline: () => { online = false; render(); }, setAuto: (value) => { const toggle = all(root).find((node) => node.id === 'list-chat-auto-toggle'); toggle.checked = value; toggle.dispatchEvent(new Event('change')); render(); }, restore: () => { globalThis.document = previous; } };
}
test('the panel names itself, explains the empty state with the three example questions and the exact controls', async () => {
  const f = await fixture({}, []);
  try {
    assert.ok(text(f.root).includes('Asistente de lista'));
    assert.equal(f.get('empty').textContent, empty);
    assert.equal(f.get('send').textContent, 'Enviar');
    assert.equal(f.get('reset').textContent, 'Nueva conversación');
    assert.ok(all(f.root).some((node) => node.tagName === 'label' && node.attrs.for === 'list-chat-request' && node.textContent === 'Pregunta sobre esta lista'));
    const buttons = all(f.get('examples')).filter((node) => node.tagName === 'button');
    assert.deepEqual(buttons.map((node) => node.textContent), examples);
    assert.equal(f.get('request').maxLength, 2000);
    assert.equal(f.get('request').disabled, false);
    for (const [index, example] of examples.entries()) {
      f.get(`example-${index}`).dispatchEvent(new Event('click'));
      assert.equal(f.controller.request, example);
      assert.equal(f.get('request').value, example);
    }
    assert.equal(f.calls.some(([kind]) => kind === 'prepare' || kind === 'run'), false);
  } finally { f.restore(); }
});
test('a turn renders the conversation oldest first as plain text and announces a re-read before the reply', async () => {
  const f = await fixture({ runAiRequest: async () => ({ cancelled: false, result: chatResult({ listChanged: true }) }) });
  try {
    const before = text(f.get('conversation'));
    assert.ok(before.indexOf('¿Qué pista quitarías?') < before.indexOf('La segunda: comparte tonalidad con la tercera.'));
    assert.equal(f.get('empty').hidden, true);
    f.get('request').value = question; f.get('request').dispatchEvent(new Event('input'));
    f.get('send').dispatchEvent(new Event('click')); await new Promise((resolve) => setImmediate(resolve));
    assert.ok(text(f.get('conversation')).includes(reply));
    const turns = f.get('conversation').children;
    assert.equal(turns.at(-1).children[0].textContent, readAgain);
    assert.equal(turns.at(-1).children.at(-1).textContent, reply);
    assert.equal(f.get('request').value, '');
    assert.ok(!all(f.root).some((node) => ['img', 'script'].includes(node.tagName)));
    assert.equal(f.get('error').hidden, true);
  } finally { f.restore(); }
});
test('a reply that did not re-read the list has no announcement', async () => {
  const f = await fixture();
  try {
    f.get('request').value = question; f.get('request').dispatchEvent(new Event('input'));
    await f.controller.send(); f.render();
    assert.ok(!text(f.root).includes(readAgain));
  } finally { f.restore(); }
});
test('while a turn runs the box and Enviar are disabled and a line says the assistant is reading the list', async () => {
  let finish; let runs = 0; const f = await fixture({ runAiRequest: () => { runs++; return new Promise((resolve) => { finish = resolve; }); } });
  try {
    f.get('request').value = question; f.get('request').dispatchEvent(new Event('input'));
    f.get('send').dispatchEvent(new Event('click'));
    assert.equal(f.get('pending').hidden, false);
    assert.equal(f.get('pending').textContent, reading);
    assert.equal(f.get('send').disabled, true);
    assert.equal(f.get('request').disabled, true);
    assert.equal(f.get('reset').disabled, true);
    assert.equal(f.get('empty').hidden, true);
    await new Promise((resolve) => setImmediate(resolve));
    assert.equal(runs, 1);
    finish({ cancelled: false, result: chatResult() }); await new Promise((resolve) => setImmediate(resolve));
    assert.equal(f.get('pending').hidden, true);
    assert.equal(f.get('request').disabled, false);
    assert.equal(f.get('request').value, '');
    assert.ok(text(f.get('conversation')).includes(reply));
  } finally { f.restore(); }
});
test('a failure shows the existing Spanish error text and keeps the typed question in the box', async () => {
  const f = await fixture({ runAiRequest: async () => { throw Object.assign(new Error('provider down'), { code: 'ai_request_failed' }); } });
  try {
    f.get('request').value = question; f.get('request').dispatchEvent(new Event('input'));
    f.get('send').dispatchEvent(new Event('click')); await new Promise((resolve) => setImmediate(resolve));
    assert.equal(f.get('error').hidden, false);
    assert.equal(f.get('error').textContent, providerError);
    assert.equal(f.get('request').value, question);
    assert.equal(f.get('request').disabled, false);
    assert.equal(f.get('send').disabled, false);
  } finally { f.restore(); }
});
test('Nueva conversación empties the panel back to its empty state', async () => {
  const f = await fixture();
  try {
    assert.equal(f.get('empty').hidden, true);
    assert.ok(text(f.get('conversation')).includes('¿Qué pista quitarías?'));
    f.get('reset').dispatchEvent(new Event('click')); await new Promise((resolve) => setImmediate(resolve));
    assert.deepEqual(f.calls.at(-1), ['reset']);
    assert.equal(f.get('conversation').children.length, 0);
    assert.equal(f.get('empty').hidden, false);
    assert.equal(f.get('empty').textContent, empty);
    assert.equal(f.get('request').value, '');
  } finally { f.restore(); }
});
test('the chat disclosure and the exact send viewer stay available, and inspecting sends nothing', async () => {
  const f = await fixture();
  try {
    assert.match(f.get('disclosure').textContent, /nunca rutas de archivo/i);
    assert.equal(f.get('payload').hidden, true);
    f.get('request').value = question; f.get('request').dispatchEvent(new Event('input'));
    await f.controller.send(); f.render();
    assert.equal(f.get('payload').hidden, false);
    assert.equal(f.get('payload').children[0].textContent, 'Ver lo que se envía');
    assert.ok(text(f.get('preview-lines')).includes('nunca rutas de archivo'));
    f.get('payload').open = true; f.get('payload').dispatchEvent(new Event('toggle'));
    await new Promise((resolve) => setImmediate(resolve));
    assert.deepEqual(f.calls.at(-1), ['payload', { previewId: uuid }]);
    assert.equal(f.get('payload-body').textContent, '{"model":"deepseek","messages":[]}');
    assert.equal(f.calls.filter(([kind]) => kind === 'run').length, 1);
  } finally { f.restore(); }
});
test('a reply with proposed changes shows «Cambios propuestos» with one card per action under the conversation', async () => {
  const f = await fixture({}, ['Pregunta previa', 'Respuesta previa'], [replaceAction(), moveAction()]);
  try {
    assert.equal(f.get('proposed').hidden, false);
    assert.equal(f.get('proposed-heading').textContent, 'Cambios propuestos');
    const cards = f.get('proposed-actions').children;
    assert.equal(cards.length, 2);
    assert.equal(cards[0].children[0].textContent, 'Reemplazar 2. Segunda por Reemplazo');
    assert.equal(cards[0].children[1].textContent, 'Choca de tonalidad con la tercera');
    assert.equal(cards[1].children[0].textContent, 'Mover 3. Tercera a la posición 1');
    assert.equal(cards[1].children[1].textContent, 'Sube la energía del inicio');
    const buttons = all(f.get('proposed-actions')).filter((node) => node.tagName === 'button');
    assert.deepEqual(buttons.map((node) => node.textContent), ['Aplicar', 'Aplicar']);
    assert.equal(buttons[0].disabled, false);
    assert.equal(f.get('dropped').hidden, true);
    assert.equal(f.get('apply-0'), buttons[0]);
    const order = f.root.children[0].children.map((node) => node.id);
    assert.ok(order.indexOf('list-chat-conversation') < order.indexOf('list-chat-proposed'), order.join(','));
    assert.ok(order.indexOf('list-chat-proposed') < order.indexOf('list-chat-request-field'));
  } finally { f.restore(); }
});
test('a reply with no proposed changes keeps «Cambios propuestos» out of the panel', async () => {
  const f = await fixture();
  try {
    assert.equal(f.get('proposed').hidden, true);
  } finally { f.restore(); }
});
test('a dropped count is explained with the exact line', async () => {
  const f = await fixture({ runAiRequest: async () => ({ cancelled: false, result: chatResult({ droppedActions: 2 }) }) });
  try {
    f.get('request').value = question; f.get('request').dispatchEvent(new Event('input'));
    await f.controller.send(); f.render();
    assert.equal(f.get('dropped').hidden, false);
    assert.equal(f.get('dropped').textContent, 'Se descartaron 2 cambios que no se pueden aplicar.');
    assert.equal(f.get('proposed').hidden, false);
  } finally { f.restore(); }
});
test('«Aplicar» sends the action id, redraws the remaining cards and says the change can be undone', async () => {
  const remaining = moveAction({ position: 1, to: 2 });
  const f = await fixture({ aiChatApply: async (input) => { f.calls.push(['apply', input]); return { review: appliedReview, actions: [remaining] }; } }, ['Pregunta previa', 'Respuesta previa'], [replaceAction(), moveAction()]);
  try {
    assert.equal(f.get('proposed-actions').children.length, 2);
    f.get('apply-0').dispatchEvent(new Event('click')); await tick();
    assert.deepEqual(f.calls.at(-1), ['apply', { actionId: uuid }]);
    assert.equal(f.applied.length, 1);
    assert.equal(f.get('notice').hidden, false);
    assert.equal(f.get('notice').textContent, appliedNotice);
    assert.equal(f.get('proposed-actions').children.length, 1);
    assert.equal(f.get('proposed-actions').children[0].children[0].textContent, 'Mover 1. Tercera a la posición 2');
    assert.equal(f.get('apply-0').disabled, false);
    assert.equal(f.calls.filter(([kind]) => kind === 'run').length, 0);
  } finally { f.restore(); }
});
test('the cards are disabled while anything runs and when the app cannot act', async () => {
  let finish;
  const f = await fixture({ runAiRequest: () => new Promise((resolve) => { finish = resolve; }) }, ['Pregunta previa', 'Respuesta previa'], [replaceAction()]);
  try {
    f.setAuto(false);
    f.get('request').value = question; f.get('request').dispatchEvent(new Event('input'));
    f.get('send').dispatchEvent(new Event('click'));
    assert.equal(f.get('apply-0').disabled, true);
    await tick();
    finish({ cancelled: false, result: chatResult({ actions: [replaceAction()] }) }); await tick();
    assert.equal(f.get('apply-0').disabled, false);
    f.offline();
    assert.equal(f.get('apply-0').disabled, true);
  } finally { f.restore(); }
});
test('a stale apply shows the existing Spanish error text and removes the cards', async () => {
  const f = await fixture({ aiChatApply: async () => { throw Object.assign(new Error('gone'), { code: 'stale_ai' }); } }, ['Pregunta previa', 'Respuesta previa'], [replaceAction()]);
  try {
    f.get('apply-0').dispatchEvent(new Event('click')); await tick();
    assert.equal(f.get('error').hidden, false);
    assert.equal(f.get('error').textContent, staleText);
    assert.equal(f.get('proposed').hidden, true);
  } finally { f.restore(); }
});
test('the whole panel disables when the app cannot act, and the reply is never injected as markup', async () => {
  const f = await fixture({ runAiRequest: async () => ({ cancelled: false, result: chatResult({ text: '<img src=x> sin datos suficientes', conversation: history(question, '<img src=x> sin datos suficientes') }) }) });
  try {
    f.get('request').value = question; f.get('request').dispatchEvent(new Event('input'));
    await f.controller.send(); f.render();
    assert.ok(text(f.get('conversation')).includes('<img src=x> sin datos suficientes'));
    f.offline();
    for (const id of ['send', 'reset', 'request']) assert.equal(f.get(id).disabled, true, id);
    assert.ok(!all(f.root).some((node) => node.tagName === 'img'));
  } finally { f.restore(); }
});
const extendCard = { actionId: uuid, type: 'extend', to: 20, reason: 'La lista se quedó en cuatro pistas' };
const variantCard = { actionId: uuid2, type: 'use_variant', variant: 'adventurous', trackCount: 20, reason: 'La exploratoria entra sin perder el orden' };
test('the two new proposal shapes are drawn as their own cards with «Aplicar»', async () => {
  const f = await fixture({}, ['Pregunta previa', 'Respuesta previa'], [extendCard, variantCard]);
  try {
    assert.equal(f.get('proposed').hidden, false);
    const cards = f.get('proposed-actions').children;
    assert.equal(cards.length, 2);
    assert.equal(cards[0].children[0].textContent, 'Ampliar la lista a 20 pistas');
    assert.equal(cards[0].children[1].textContent, 'La lista se quedó en cuatro pistas');
    assert.equal(cards[1].children[0].textContent, 'Usar la alternativa exploratoria (20 pistas)');
    assert.equal(cards[1].children[1].textContent, 'La exploratoria entra sin perder el orden');
    const buttons = all(f.get('proposed-actions')).filter((node) => node.tagName === 'button');
    assert.deepEqual(buttons.map((node) => node.textContent), ['Aplicar', 'Aplicar']);
    assert.equal(buttons[0].id, 'list-chat-apply-0');
    assert.equal(buttons[1].id, 'list-chat-apply-1');
    assert.equal(buttons[1].disabled, false);
    assert.equal(f.get('apply-1').attrs['aria-label'], 'Aplicar: Usar la alternativa exploratoria (20 pistas)');
  } finally { f.restore(); }
});
const cardUuid = (n) => `${String(n).repeat(8)}-1111-4111-8111-111111111111`;
const removeCard = { actionId: cardUuid(3), type: 'remove', position: 2, title: 'Segunda', artist: 'DJ Dos', reason: 'Choca de tonalidad con la tercera' };
const addCard = { actionId: cardUuid(4), type: 'add', position: 3, track: { title: 'Nueva', artist: 'DJ Cinco', bpm: 126, key: '10A' }, reason: 'Sube la energía del cierre' };
const replaceWithCard = { actionId: cardUuid(5), type: 'replace_with', position: 2, title: 'Segunda', artist: 'DJ Dos', track: { title: 'Otra', artist: 'DJ Seis', bpm: 124, key: '9A' }, reason: 'Encaja mejor con la tercera' };
const reorderCard = { actionId: cardUuid(6), type: 'reorder', moved: 3, reason: 'La curva de energía sube antes' };
const undoCard = { actionId: cardUuid(7), type: 'undo', reason: 'El orden anterior era mejor' };
test('S6: the five new cards show their exact sentence, the reason and one Aplicar each', async () => {
  const f = await fixture({}, ['Pregunta previa', 'Respuesta previa'], [removeCard, addCard, replaceWithCard, reorderCard, undoCard]);
  try {
    assert.equal(f.get('proposed').hidden, false);
    const cards = f.get('proposed-actions').children;
    assert.equal(cards.length, 5);
    assert.deepEqual(cards.map((card) => card.children[0].textContent), [
      'Quitar 2. Segunda',
      'Agregar Nueva en la posición 3',
      'Reemplazar 2. Segunda por Otra',
      'Reordenar la lista (3 pistas cambian de lugar)',
      'Deshacer el último cambio',
    ]);
    assert.deepEqual(cards.map((card) => card.children[1].textContent), [removeCard.reason, addCard.reason, replaceWithCard.reason, reorderCard.reason, undoCard.reason]);
    const buttons = all(f.get('proposed-actions')).filter((node) => node.tagName === 'button');
    assert.deepEqual(buttons.map((node) => node.textContent), ['Aplicar', 'Aplicar', 'Aplicar', 'Aplicar', 'Aplicar']);
    assert.equal(f.get('apply-0').attrs['aria-label'], 'Aplicar: Quitar 2. Segunda');
    assert.equal(f.get('apply-4').attrs['aria-label'], 'Aplicar: Deshacer el último cambio');
  } finally { f.restore(); }
});
test('S2: two or more proposals offer «Aplicar todo», which applies them in order and reports the count', async () => {
  const seen = [];
  const f = await fixture({ aiChatApply: async (input) => { seen.push(input.actionId); return { review: appliedReview, actions: [] }; } }, ['Pregunta previa', 'Respuesta previa'], [removeCard, undoCard]);
  try {
    assert.equal(f.get('apply-all').hidden, false);
    assert.equal(f.get('apply-all').textContent, 'Aplicar todo');
    assert.equal(f.get('apply-all').disabled, false);
    f.get('apply-all').dispatchEvent(new Event('click')); await tick();
    assert.deepEqual(seen, [removeCard.actionId, undoCard.actionId]);
    assert.equal(f.get('notice').hidden, false);
    assert.equal(f.get('notice').textContent, 'Se aplicaron 2 de 2 cambios.');
  } finally { f.restore(); }
});
test('S2: «Aplicar todo» is not offered for a single change', async () => {
  const f = await fixture({}, ['Pregunta previa', 'Respuesta previa'], [removeCard]);
  try {
    assert.equal(f.get('proposed').hidden, false);
    assert.equal(f.get('apply-all').hidden, true);
  } finally { f.restore(); }
});
// --- S9: automatic apply with one batch undo ---
const autoSentence = 'Aplicar los cambios automáticamente';
const undoBatchSentence = 'Deshacer estos cambios';
const sendReply = async (f) => {
  f.get('request').value = question; f.get('request').dispatchEvent(new Event('input'));
  f.get('send').dispatchEvent(new Event('click')); await tick();
};
test('S9: the window offers «Aplicar los cambios automáticamente», on by default and kept across conversations', async () => {
  const f = await fixture();
  try {
    assert.equal(f.get('auto-toggle').checked, true);
    assert.equal(f.controller.autoApply, true);
    const label = all(f.get('auto')).find((node) => node.tagName === 'label');
    assert.equal(label.textContent, autoSentence);
    assert.equal(label.attrs.for, 'list-chat-auto-toggle');
    assert.equal(f.get('auto-applied').hidden, true);
    assert.equal(f.get('undo-batch').textContent, undoBatchSentence);
    f.setAuto(false);
    assert.equal(f.controller.autoApply, false);
    assert.equal(f.get('auto-toggle').checked, false);
    await f.controller.newConversation(); f.render();
    assert.equal(f.get('auto-toggle').checked, false, 'the choice is kept while the app is open');
    f.setAuto(true);
    assert.equal(f.controller.autoApply, true);
    assert.equal(f.calls.some(([kind]) => kind === 'apply'), false);
  } finally { f.restore(); }
});
test('S9: with the switch on a reply with three changes applies them at once, without cards, and offers the batch undo', async () => {
  const seen = [];
  const f = await fixture({
    runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [removeCard, reorderCard, undoCard] }) }),
    aiChatApply: async (input) => { seen.push(input.actionId); f.calls.push(['apply', input]); return { review: appliedReview, actions: [] }; },
  }, ['Pregunta previa', 'Respuesta previa'], []);
  try {
    await sendReply(f);
    assert.deepEqual(seen, [removeCard.actionId, reorderCard.actionId, undoCard.actionId], 'the shown order is kept');
    assert.equal(f.applied.length, 3, 'every change is handed to the screen as a normal edit');
    assert.equal(f.get('auto-applied').hidden, false);
    assert.equal(f.get('auto-notice').textContent, 'Se aplicaron 3 cambios.');
    assert.deepEqual(f.get('auto-list').children.map((node) => node.textContent), ['Quitar 2. Segunda', 'Reordenar la lista (3 pistas cambian de lugar)', 'Deshacer el último cambio']);
    assert.equal(f.get('undo-batch').hidden, false);
    assert.equal(f.get('undo-batch').disabled, false);
    assert.equal(f.get('proposed').hidden, true, 'no card is left to approve');
    assert.equal(f.get('error').hidden, true);
  } finally { f.restore(); }
});
test('S9: the batch stops at the first failure, reports how many of how many and leaves the rest as cards', async () => {
  const seen = [];
  const f = await fixture({
    runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [removeCard, reorderCard, undoCard] }) }),
    aiChatApply: async (input) => {
      seen.push(input.actionId);
      if (input.actionId === reorderCard.actionId) throw Object.assign(new Error('bad'), { code: 'invalid_params' });
      return { review: appliedReview, actions: [reorderCard, undoCard] };
    },
  }, ['Pregunta previa', 'Respuesta previa'], []);
  try {
    await sendReply(f);
    assert.deepEqual(seen, [removeCard.actionId, reorderCard.actionId], 'the batch stops at the first failure');
    assert.equal(f.get('auto-notice').textContent, 'Se aplicaron 1 de 3 cambios.');
    assert.deepEqual(f.get('auto-list').children.map((node) => node.textContent), ['Quitar 2. Segunda']);
    assert.equal(f.get('error').textContent, 'Revisa los datos de la operación y sus límites antes de intentarlo de nuevo.');
    assert.deepEqual(f.get('proposed-actions').children.map((card) => card.children[0].textContent), ['Reordenar la lista (3 pistas cambian de lugar)', 'Deshacer el último cambio']);
    assert.equal(f.get('apply-0').textContent, 'Aplicar');
    assert.equal(f.get('undo-batch').hidden, false, 'the steps that were applied can still be undone');
  } finally { f.restore(); }
});
test('S9: a use_variant is never applied automatically and stays as a card with «Aplicar»', async () => {
  const seen = [];
  const f = await fixture({
    runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [variantCard, removeCard] }) }),
    aiChatApply: async (input) => { seen.push(input.actionId); return { review: appliedReview, actions: [variantCard] }; },
  }, ['Pregunta previa', 'Respuesta previa'], []);
  try {
    await sendReply(f);
    assert.deepEqual(seen, [removeCard.actionId], 'the alternative is never applied by the batch');
    assert.equal(f.calls.some(([kind]) => kind === 'select'), false);
    assert.equal(f.get('proposed').hidden, false);
    assert.deepEqual(f.get('proposed-actions').children.map((card) => card.children[0].textContent), ['Usar la alternativa exploratoria (20 pistas)']);
    assert.equal(f.get('apply-0').textContent, 'Aplicar');
    assert.equal(f.get('auto-notice').textContent, 'Se aplicaron 1 cambios.');
  } finally { f.restore(); }
});
test('S9: «Deshacer estos cambios» undoes exactly the applied steps and then disappears', async () => {
  const undos = [];
  const f = await fixture({
    runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [removeCard, reorderCard] }) }),
    aiChatApply: async (input) => { f.calls.push(['apply', input]); return { review: appliedReview, actions: input.actionId === removeCard.actionId ? [reorderCard] : [] }; },
    reviewUndo: async (input) => { undos.push({ ...input }); return { ...appliedReview, reviewId: undos.length === 1 ? uuid : uuid2 }; },
  }, ['Pregunta previa', 'Respuesta previa'], []);
  try {
    await sendReply(f);
    assert.equal(f.get('auto-notice').textContent, 'Se aplicaron 2 cambios.');
    f.get('undo-batch').dispatchEvent(new Event('click')); await tick();
    assert.deepEqual(undos, [{ reviewId: uuid2 }, { reviewId: uuid }], 'one undo per applied step, each on the review it minted');
    assert.equal(f.applied.length, 4, 'each undo is handed to the screen as a normal edit');
    assert.equal(f.get('auto-applied').hidden, true);
    assert.equal(f.get('undo-batch').hidden, true);
    assert.equal(f.get('error').hidden, true);
  } finally { f.restore(); }
});
test('S9: the batch undo is retired by any other edit of the list', async () => {
  const f = await fixture({
    runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [removeCard, reorderCard] }) }),
    aiChatApply: async (input) => { f.calls.push(['apply', input]); return { review: appliedReview, actions: input.actionId === removeCard.actionId ? [reorderCard] : [] }; },
    reviewUndo: async () => appliedReview,
  }, ['Pregunta previa', 'Respuesta previa'], []);
  try {
    await sendReply(f);
    assert.equal(f.get('undo-batch').hidden, false);
    f.controller.reviewReplaced(); f.render();
    assert.equal(f.get('auto-applied').hidden, true);
    assert.equal(f.get('undo-batch').hidden, true);
    f.get('undo-batch').dispatchEvent(new Event('click')); await tick();
    assert.equal(f.calls.some(([kind]) => kind === 'undo'), false);
  } finally { f.restore(); }
});
test('S9: with the switch off a reply keeps its cards, «Aplicar» and «Aplicar todo» as before', async () => {
  const f = await fixture({ runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [removeCard, reorderCard] }) }) }, ['Pregunta previa', 'Respuesta previa'], []);
  try {
    f.setAuto(false);
    await sendReply(f);
    assert.equal(f.calls.some(([kind]) => kind === 'apply'), false, 'nothing is applied without the switch');
    assert.equal(f.get('auto-applied').hidden, true);
    assert.equal(f.get('proposed').hidden, false);
    assert.equal(f.get('proposed-actions').children.length, 2);
    assert.equal(f.get('apply-all').hidden, false);
    assert.equal(f.get('apply-0').disabled, false);
  } finally { f.restore(); }
});
test('S9: a batch undo without the undo bridge says the app must be updated and changes nothing', async () => {
  const f = await fixture({
    runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [removeCard, reorderCard] }) }),
    aiChatApply: async (input) => { f.calls.push(['apply', input]); return { review: appliedReview, actions: input.actionId === removeCard.actionId ? [reorderCard] : [] }; },
  }, ['Pregunta previa', 'Respuesta previa'], []);
  try {
    await sendReply(f);
    f.get('undo-batch').dispatchEvent(new Event('click')); await tick();
    assert.equal(f.get('error').textContent, 'Actualiza la aplicación para deshacer cambios.');
    assert.equal(f.calls.filter(([kind]) => kind === 'apply').length, 2);
  } finally { f.restore(); }
});
// --- S15: fit the list to a period, card and report ---
const periodCard = { actionId: cardUuid(8), type: 'period', yearMin: 1980, yearMax: 1999, outside: 7, reason: 'El DJ pidió solo los 80 y los 90' };
const periodAnswer = (patch = {}) => ({ yearMin: 1980, yearMax: 1999, replaced: 3, kept: [{ position: 1, title: 'Apertura', year: 1975, reason: 'protected' }, { position: 6, title: 'Rareza', year: null, reason: 'no_candidate' }], ...patch });
const periodCardText = 'Ajustar la lista a 1980–1999 (7 pistas fuera de época)';
test('S15: the period card shows its exact sentence, the reason and one «Aplicar»', async () => {
  const f = await fixture({}, ['Pregunta previa', 'Respuesta previa'], [periodCard]);
  try {
    assert.equal(f.get('proposed').hidden, false);
    const cards = f.get('proposed-actions').children;
    assert.equal(cards.length, 1);
    assert.equal(cards[0].children[0].textContent, periodCardText);
    assert.equal(cards[0].children[1].textContent, periodCard.reason);
    assert.equal(f.get('apply-0').textContent, 'Aplicar');
    assert.equal(f.get('apply-0').attrs['aria-label'], `Aplicar: ${periodCardText}`);
    assert.equal(f.get('apply-0').disabled, false);
    assert.equal(f.get('period').hidden, true);
  } finally { f.restore(); }
});
test('S15: applying the period card says what was replaced and lists the tracks that stayed out', async () => {
  const f = await fixture({ aiChatApply: async (input) => { f.calls.push(['apply', input]); return { review: appliedReview, actions: [], period: periodAnswer() }; } }, ['Pregunta previa', 'Respuesta previa'], [periodCard]);
  try {
    f.get('apply-0').dispatchEvent(new Event('click')); await tick();
    assert.deepEqual(f.calls.at(-1), ['apply', { actionId: periodCard.actionId }]);
    assert.equal(f.get('period').hidden, false);
    assert.equal(f.get('period-notice').textContent, 'Se reemplazaron 3 pistas.');
    assert.equal(f.get('period-kept-heading').hidden, false);
    assert.equal(f.get('period-kept-heading').textContent, 'Quedan 2 fuera de época:');
    assert.deepEqual(f.get('period-kept').children.map((node) => node.textContent), ['1. Apertura (1975) — protegida', '6. Rareza (sin año) — no hay otra de esa época que mezcle']);
    assert.equal(f.get('notice').hidden, true, 'the replaced line is said once');
    assert.equal(f.get('proposed').hidden, true);
  } finally { f.restore(); }
});
test('S15: a period that kept nothing shows only the replaced line', async () => {
  const f = await fixture({ aiChatApply: async () => ({ review: appliedReview, actions: [], period: periodAnswer({ replaced: 20, kept: [] }) }) }, ['Pregunta previa', 'Respuesta previa'], [periodCard]);
  try {
    f.get('apply-0').dispatchEvent(new Event('click')); await tick();
    assert.equal(f.get('period').hidden, false);
    assert.equal(f.get('period-notice').textContent, 'Se reemplazaron 20 pistas.');
    assert.equal(f.get('period-kept-heading').hidden, true);
    assert.equal(f.get('period-kept').children.length, 0);
  } finally { f.restore(); }
});
test('S15: the report also shows after an automatic batch', async () => {
  const f = await fixture({
    runAiRequest: async () => ({ cancelled: false, result: chatResult({ actions: [periodCard, removeCard] }) }),
    aiChatApply: async (input) => {
      f.calls.push(['apply', input]);
      return { review: appliedReview, actions: [], ...(input.actionId === periodCard.actionId ? { period: periodAnswer({ replaced: 4, kept: [{ position: 1, title: 'Apertura', year: 1975, reason: 'protected' }] }) } : {}) };
    },
  }, ['Pregunta previa', 'Respuesta previa'], []);
  try {
    await sendReply(f);
    assert.equal(f.get('auto-applied').hidden, false);
    assert.equal(f.get('auto-notice').textContent, 'Se aplicaron 2 cambios.');
    assert.deepEqual(f.get('auto-list').children.map((node) => node.textContent), [periodCardText, 'Quitar 2. Segunda']);
    assert.equal(f.get('period').hidden, false);
    assert.equal(f.get('period-notice').textContent, 'Se reemplazaron 4 pistas.');
    assert.equal(f.get('period-kept-heading').textContent, 'Quedan 1 fuera de época:');
    assert.deepEqual(f.get('period-kept').children.map((node) => node.textContent), ['1. Apertura (1975) — protegida']);
    assert.equal(f.get('error').hidden, true);
    assert.equal(f.get('undo-batch').hidden, false);
  } finally { f.restore(); }
});
