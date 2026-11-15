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
  return { root, controller, calls, applied, render, get: (id) => all(root).find((node) => node.id === `list-chat-${id}`) ?? all(root).find((node) => node.id === `list-chat`), offline: () => { online = false; render(); }, restore: () => { globalThis.document = previous; } };
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
