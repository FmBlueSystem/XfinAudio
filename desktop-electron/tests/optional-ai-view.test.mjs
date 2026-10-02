import assert from 'node:assert/strict';
import test from 'node:test';
import { OptionalAiController, AI_RECIPIENT, AI_CONNECTION_REQUEST } from '../.out/renderer/optional-ai.js';
import { createOptionalAiView } from '../.out/renderer/optional-ai-view.js';
class Element extends EventTarget {
  constructor(tag = 'div') { super(); this.tagName = tag; }
  children = []; attrs = {}; textContent = ''; value = ''; checked = false; disabled = false; hidden = false;
  setAttribute(key, value) { this.attrs[key] = String(value); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  set innerHTML(_) { throw new Error('Unsafe HTML'); }
}
const all = (node) => [node, ...node.children.flatMap(all)]; const text = (node) => [node.textContent, ...node.children.map(text)].join(' ');
const uuid = '12345678-1234-4123-8123-123456789012';
async function fixture(surface = 'library', resultPatch = {}) {
  const previous = globalThis.document; globalThis.document = { createElement: (tag) => new Element(tag) }; let online = true; const calls = []; const root = new Element(); let render = () => {};
  const snapshot = { revision: 'a'.repeat(64), enabled: true, provider: 'nan', credentialLabel: 'fixture.env', configured: true, recipient: AI_RECIPIENT };
  const kinds = { library: 'filters', prep: 'intent', editor: 'editor_request', saved: 'saved_selection', review: 'commentary', metadata: 'commentary', live: 'commentary', connection: 'connection' };
  const api = { getAiStatus: async () => snapshot, saveAiSettings: async (input) => ({ ...snapshot, ...input }), chooseAiCredential: async () => snapshot, clearAiCredential: async () => ({ ...snapshot, configured: false, credentialLabel: null }), prepareAiRequest: async (input) => { calls.push(['prepare', input]); return { previewId: uuid, surface, recipient: AI_RECIPIENT, disclosure: ['Datos autorizados de la pantalla, nunca audio'], requestPreview: '[ruta omitida] <img src=x>' }; }, runAiRequest: async (input) => { calls.push(['ask', input]); return { cancelled: false, result: { resultId: uuid, surface, kind: kinds[surface], title: '<script>modelo</script>', text: '<img src=x> Comentario externo', proposal: { genres: ['house'] }, canApply: true, ...resultPatch } }; }, applyAiSuggestion: async (input) => { calls.push(['apply', input]); return { surface, data: { genres: ['house'] } }; } };
  const controller = new OptionalAiController(api, { canAct: () => online, changed: () => render(), dirtyChanged: () => {}, applied: () => {}, perform: async (_label, task, apply, fail) => { try { apply(await task(), true); } catch (error) { fail(error); } } });
  render = createOptionalAiView(root, controller, { canAct: () => online }); controller.setContext(surface, surface === 'review' ? { reviewId: uuid } : surface === 'editor' ? { editId: uuid } : surface === 'live' ? { sessionId: uuid, revision: 0 } : {}, 'local1'); await controller.load(); render();
  return { root, controller, calls, render, get: (id) => all(root).find((node) => node.id === `optional-ai-${id}`), block: () => { online = false; controller.invalidate(); render(); }, restore: () => { globalThis.document = previous; } };
}
test('configuration is truthful and accessible with source chooser, no key or endpoint input', async () => {
  const f = await fixture(); try { assert.match(text(f.root), /No se ha comprobado la conexión/); assert.match(text(f.root), /fixture.env/); assert.ok(text(f.root).includes(AI_RECIPIENT)); assert.ok(!all(f.root).some((node) => node.tagName === 'input' && ['password', 'file', 'url'].includes(node.type))); for (const id of ['enabled', 'request', 'consent']) assert.ok(all(f.root).some((node) => node.tagName === 'label' && node.attrs.for === `optional-ai-${id}`)); assert.equal(f.get('consent').checked, false); assert.equal(f.get('ask').disabled, true); const request = f.get('request'); f.render(); assert.equal(f.get('request'), request); assert.equal(request.maxLength, 2000); } finally { f.restore(); }
});
test('preview presents redacted data and fresh unchecked consent before an explicit Ask; result remains text-only until Apply', async () => {
  const f = await fixture(); try { f.get('request').value = 'house'; f.get('request').dispatchEvent(new Event('input')); f.get('prepare').dispatchEvent(new Event('click')); await new Promise((resolve) => setImmediate(resolve)); assert.match(text(f.get('preview')), /ruta omitida/); assert.equal(f.get('consent').checked, false); assert.equal(f.calls.some(([kind]) => kind === 'ask'), false); f.get('consent').checked = true; f.get('consent').dispatchEvent(new Event('change')); f.get('ask').dispatchEvent(new Event('click')); await new Promise((resolve) => setImmediate(resolve)); assert.ok(text(f.get('result')).includes('<script>modelo</script>')); assert.ok(!all(f.root).some((node) => ['img', 'script'].includes(node.tagName))); assert.equal(f.calls.some(([kind]) => kind === 'apply'), false); f.get('apply').dispatchEvent(new Event('click')); await new Promise((resolve) => setImmediate(resolve)); assert.equal(f.calls.filter(([kind]) => kind === 'apply').length, 1); } finally { f.restore(); }
});
test('fact explanations and connection use fixed requests, review disclosure names all shared facts, commentary cannot Apply', async () => {
  for (const surface of ['review', 'metadata', 'live', 'connection']) { const f = await fixture(surface); try { assert.equal(f.get('request-field').hidden, true); if (surface === 'review') for (const field of ['títulos', 'artistas', 'ordenados', 'calidad', 'preparación']) assert.ok(text(f.root).includes(field)); if (surface === 'connection') assert.ok(text(f.root).includes(AI_CONNECTION_REQUEST)); await f.controller.prepare(); f.controller.setConsent(true); await f.controller.ask(); assert.equal(f.get('apply').hidden, true); assert.match(text(f.get('result')), /IA/); } finally { f.restore(); } }
});
test('pending and offline controls disable every action, showing cancellation limits and preserving no late consent', async () => {
  const f = await fixture(); try { f.controller.pending = 'ask'; f.render(); assert.match(text(f.get('pending')), /enviados.*recuperar/); for (const node of all(f.root).filter((node) => ['button', 'input', 'textarea'].includes(node.tagName))) assert.equal(node.disabled, true, node.id); f.controller.pending = null; f.block(); for (const node of all(f.root).filter((node) => ['button', 'input', 'textarea'].includes(node.tagName))) assert.equal(node.disabled, true, node.id); assert.equal(f.get('error').attrs.role, 'alert'); assert.equal(f.get('consent').checked, false); } finally { f.restore(); }
});
test('a completed connection test is described separately from mere credential-source configuration', async () => {
  const f = await fixture('connection'); try { await f.controller.prepare(); f.controller.setConsent(true); await f.controller.ask(); assert.doesNotMatch(f.get('status').textContent, /No se ha comprobado la conexión/); assert.match(f.get('status').textContent, /resultado de la prueba/); } finally { f.restore(); }
});
test('all eight contexts share one draft while only global connection shows credential settings',async()=>{
 for(const surface of ['library','prep','review','saved','editor','metadata','live','connection']){
  const f=await fixture(surface);try{assert.equal(f.get('config').hidden,surface!=='connection');assert.equal(f.get('settings-link').hidden,surface==='connection');assert.equal(f.calls.length,0);const enabled=f.get('enabled');f.controller.setEnabled(false);f.render();assert.equal(f.get('enabled'),enabled);assert.equal(f.controller.dirty,true);assert.match(f.get('config-summary').textContent,/sin guardar/);assert.equal(f.get('consent').checked,false);}finally{f.restore();}
 }
});
