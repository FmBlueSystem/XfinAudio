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
async function fixture(surface = 'library', resultPatch = {}, contextPatch = null) {
  const previous = globalThis.document; globalThis.document = { createElement: (tag) => new Element(tag) }; let online = true; let busy = false; const calls = []; const root = new Element(); let render = () => {};
  const snapshot = { revision: 'a'.repeat(64), enabled: true, provider: 'nan', credentialLabel: 'fixture.env', configured: true, recipient: AI_RECIPIENT };
  const kinds = { library: 'filters', prep: 'intent', editor: 'editor_request', saved: 'saved_selection', review: 'commentary', metadata: 'commentary', live: 'commentary', connection: 'connection' };
  const api = { getAiStatus: async () => snapshot, saveAiSettings: async (input) => ({ ...snapshot, ...input }), chooseAiCredential: async () => snapshot, clearAiCredential: async () => ({ ...snapshot, configured: false, credentialLabel: null }), prepareAiRequest: async (input) => { calls.push(['prepare', input]); return { previewId: uuid, surface, recipient: AI_RECIPIENT, disclosure: ['Datos autorizados de la pantalla, nunca audio'], requestPreview: '[ruta omitida] <img src=x>' }; }, runAiRequest: async (input) => { calls.push(['ask', input]); return { cancelled: false, result: { resultId: uuid, surface, kind: kinds[surface], title: '<script>modelo</script>', text: '<img src=x> Comentario externo', proposal: { genres: ['house'] }, canApply: true, ...resultPatch } }; }, applyAiSuggestion: async (input) => { calls.push(['apply', input]); return { surface, data: { genres: ['house'] } }; }, inspectAiPayload: async (input) => { calls.push(['aiPayload', input]); return { previewId: uuid, surface, recipient: AI_RECIPIENT, request: 'house', body: '{"model":"deepseek","messages":[]}', bytes: 31, truncated: false }; } };
  const controller = new OptionalAiController(api, { canAct: () => online && !busy, changed: () => render(), dirtyChanged: () => {}, applied: () => {}, perform: async (_label, task, apply, fail) => { try { apply(await task(), true); } catch (error) { fail(error); } } });
  render = createOptionalAiView(root, controller, { canAct: () => online && !busy, busy: () => busy }); controller.setContext(surface, contextPatch ?? (surface === 'review' ? { reviewId: uuid } : surface === 'editor' ? { editId: uuid } : surface === 'live' ? { sessionId: uuid, revision: 0 } : {}), 'local1'); await controller.load(); render();
  return { root, controller, calls, render, get: (id) => all(root).find((node) => node.id === `optional-ai-${id}`), setBusy: (value) => { busy = value; }, block: () => { online = false; controller.invalidate(); render(); }, restore: () => { globalThis.document = previous; } };
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
test('a local job keeps the Prep request editable, states the wait, and leaves the preview manual after idle', async () => {
  const f = await fixture('prep'); try {
    f.setBusy(true); f.render();
    const request = f.get('request');
    assert.equal(request.disabled, false);
    request.value = 'Sesión house';
    request.dispatchEvent(new Event('input'));
    assert.equal(f.get('local-hold').hidden, false);
    assert.match(f.get('local-hold').textContent, /operación local/i);
    assert.equal(f.get('prepare').disabled, true);
    f.get('prepare').dispatchEvent(new Event('click'));
    assert.equal(f.calls.some(([kind]) => kind === 'prepare'), false);
    assert.equal(f.calls.some(([kind]) => kind === 'run'), false);
    f.setBusy(false); f.render();
    assert.equal(f.get('request').value, 'Sesión house');
    assert.equal(f.get('local-hold').hidden, true);
    assert.equal(f.get('prepare').disabled, false);
    f.get('prepare').dispatchEvent(new Event('click'));
    await new Promise((resolve) => setImmediate(resolve));
    assert.equal(f.calls.filter(([kind]) => kind === 'prepare').length, 1);
  } finally { f.restore(); }
});
test('a completed connection test is described separately from mere credential-source configuration', async () => {
  const f = await fixture('connection'); try { await f.controller.prepare(); f.controller.setConsent(true); await f.controller.ask(); assert.doesNotMatch(f.get('status').textContent, /No se ha comprobado la conexión/); assert.match(f.get('status').textContent, /resultado de la prueba/); } finally { f.restore(); }
});
const improvementContext = (includeReplacements = false) => ({ editId: uuid, draftIds: ['a'.repeat(64), 'b'.repeat(64)], includeReplacements });
const improvementPatch = { kind: 'improvement', proposal: { orderedTrackIds: ['a1b2c3d4e5f60718'], rationale: 'x' } };
test('the editor improvement view states the instruction, the default-off replacement toggle and an accurate disclosure', async () => {
  const f = await fixture('editor', improvementPatch, improvementContext(false));
  try {
    assert.ok(text(f.root).includes('Mejorar esta playlist'));
    const toggle = f.get('include-replacements'); assert.equal(toggle.checked, false); assert.equal(toggle.disabled, false);
    assert.ok(all(f.root).some((node) => node.tagName === 'label' && node.attrs.for === 'optional-ai-include-replacements' && /reemplazos/i.test(node.textContent)));
    const disclosure = f.get('surface-disclosure').textContent;
    for (const field of ['títulos', 'artistas', 'metadatos', 'rutas', 'audio']) assert.ok(disclosure.includes(field), field);
    assert.match(disclosure, /borrador/i); assert.match(disclosure, /guardar/i); assert.match(disclosure, /sin candidatas de reemplazo/i);
    assert.equal(f.calls.length, 0);
  } finally { f.restore(); }
});
test('toggling replacements discards pending disclosure and consent, then reprepares the exact improvement context', async () => {
  const f = await fixture('editor', improvementPatch, improvementContext(false));
  try {
    f.get('request').value = 'Mejorar esta playlist'; f.get('request').dispatchEvent(new Event('input'));
    f.get('prepare').dispatchEvent(new Event('click')); await new Promise((resolve) => setImmediate(resolve));
    assert.equal(f.get('preview').hidden, false);
    f.get('consent').checked = true; f.get('consent').dispatchEvent(new Event('change')); assert.equal(f.controller.consent, true);
    const toggle = f.get('include-replacements'); toggle.checked = true; toggle.dispatchEvent(new Event('change'));
    assert.equal(f.controller.includeReplacements, true); assert.equal(f.controller.consent, false); assert.equal(f.controller.preview, null);
    f.render(); assert.equal(f.get('preview').hidden, true); assert.equal(f.get('consent').checked, false); assert.match(f.get('surface-disclosure').textContent, /posibles reemplazos/i);
    f.get('prepare').dispatchEvent(new Event('click')); await new Promise((resolve) => setImmediate(resolve));
    assert.deepEqual(f.calls.at(-1), ['prepare', { surface: 'editor', request: 'Mejorar esta playlist', context: { editId: uuid, draftIds: ['a'.repeat(64), 'b'.repeat(64)], includeReplacements: true } }]);
    assert.equal(f.calls.some(([kind]) => kind === 'ask'), false); assert.equal(f.calls.some(([kind]) => kind === 'apply'), false);
  } finally { f.restore(); }
});
test('all eight contexts share one draft while only global connection shows credential settings',async()=>{
 for(const surface of ['library','prep','review','saved','editor','metadata','live','connection']){
  const f=await fixture(surface);try{assert.equal(f.get('config').hidden,surface!=='connection');assert.equal(f.get('settings-link').hidden,surface==='connection');assert.equal(f.calls.length,0);const enabled=f.get('enabled');f.controller.setEnabled(false);f.render();assert.equal(f.get('enabled'),enabled);assert.equal(f.controller.dirty,true);assert.match(f.get('config-summary').textContent,/sin guardar/);assert.equal(f.get('consent').checked,false);}finally{f.restore();}
 }
});

test('the improvement result offers a local review action with truthful, non-applying copy', async () => {
  const f = await fixture('editor', improvementPatch, improvementContext(false));
  try {
    f.get('request').value = 'Mejorar esta playlist'; f.get('request').dispatchEvent(new Event('input'));
    await f.controller.prepare(); f.controller.setConsent(true); await f.controller.ask(); f.render();
    assert.equal(f.get('apply').textContent, 'Revisar propuesta local');
    assert.equal(f.get('apply').hidden, false);
    assert.match(f.get('apply-hint').textContent, /no cambia el borrador/i);
    assert.doesNotMatch(f.get('apply-hint').textContent, /aplicad[ao] al trabajo local/i);
    await f.controller.applySuggestion();
    assert.match(f.controller.notice, /borrador/i);
    assert.doesNotMatch(f.controller.notice, /aplicad[ao] al trabajo local/i);
  } finally { f.restore(); }
});
test('a non-improvement result keeps the original apply action copy', async () => {
  const f = await fixture('library');
  try {
    await f.controller.prepare(); f.controller.setConsent(true); await f.controller.ask(); f.render();
    assert.equal(f.get('apply').textContent, 'Aplicar propuesta al trabajo local');
    assert.match(f.get('apply-hint').textContent, /no guarda/i);
  } finally { f.restore(); }
});

// --- F2/F10: phase-aware pending feedback, elapsed timer and prepare blockers ---
test('the prepare button renders the first blocker as a hint and hides it when preparation is possible', async () => {
  const f = await fixture(); try {
    f.render();
    assert.equal(f.get('prepare').disabled, true);
    assert.equal(f.get('prepare-hint').hidden, false);
    assert.equal(f.get('prepare-hint').className, 'field-hint');
    assert.equal(f.get('prepare-hint').textContent, 'Escribe qué quieres mejorar.');
    f.get('request').value = 'Busca house'; f.get('request').dispatchEvent(new Event('input')); f.render();
    assert.equal(f.get('prepare').disabled, false);
    assert.equal(f.get('prepare-hint').hidden, true);
    assert.equal(f.get('prepare-hint').textContent, '');
  } finally { f.restore(); }
});
test('during the provider ask the panel shows phase copy, hides the local-job notice and refreshes elapsed seconds once per second', async () => {
  const realSet = globalThis.setInterval; const realClear = globalThis.clearInterval; const timers = [];
  globalThis.setInterval = (fn, ms) => { const timer = { fn, ms, cleared: false }; timers.push(timer); return timer; };
  globalThis.clearInterval = (timer) => { if (timer) timer.cleared = true; };
  const f = await fixture('prep');
  try {
    f.setBusy(true); f.controller.pending = 'prepare'; f.render();
    assert.equal(f.get('local-hold').hidden, false);
    assert.equal(f.get('pending').hidden, false);
    assert.equal(f.get('pending').textContent, 'Preparando la vista previa de datos…');
    assert.equal(timers.length, 0);
    f.controller.pending = 'ask'; f.controller.askStartedAt = Date.now() - 12000; f.render();
    assert.equal(f.get('local-hold').hidden, true);
    assert.match(f.get('pending').textContent, /Consultando a Nan Builders/);
    assert.match(f.get('pending').textContent, /· 12 s/);
    assert.match(f.get('pending').textContent, /enviados.*recuperar/);
    assert.equal(timers.length, 1); assert.equal(timers[0].ms, 1000);
    f.controller.askStartedAt = Date.now() - 15000; timers[0].fn();
    assert.match(f.get('pending').textContent, /· 15 s/);
    f.controller.pending = null; f.render();
    assert.equal(timers[0].cleared, true);
    assert.equal(f.get('pending').hidden, true);
    assert.equal(f.get('local-hold').hidden, false);
  } finally { globalThis.setInterval = realSet; globalThis.clearInterval = realClear; f.restore(); }
});

// --- F6: explicit, read-only exact payload viewer inside the disclosure block ---
test('the disclosure block offers an on-demand exact payload viewer that renders JSON as text and sends nothing', async () => {
  const f = await fixture();
  try {
    assert.equal(f.get('payload').hidden, true);
    assert.equal(f.get('payload-body').textContent, '');
    f.get('request').value = 'house'; f.get('request').dispatchEvent(new Event('input'));
    f.get('prepare').dispatchEvent(new Event('click')); await new Promise((resolve) => setImmediate(resolve));
    assert.equal(f.get('payload').hidden, false);
    assert.equal(f.get('payload').children[0].textContent, 'Ver payload exacto');
    assert.match(f.get('payload-hint').textContent, /solo lectura/i);
    assert.match(f.get('payload-hint').textContent, /no se envía nada/i);
    assert.equal(f.calls.some(([kind]) => kind === 'aiPayload'), false);
    f.get('payload').open = true; f.get('payload').dispatchEvent(new Event('toggle'));
    await new Promise((resolve) => setImmediate(resolve));
    assert.deepEqual(f.calls.at(-1), ['aiPayload', { previewId: uuid }]);
    assert.equal(f.get('payload-body').textContent, f.controller.payload.body);
    assert.equal(f.get('payload-body').children.length, 0);
    assert.equal(f.calls.some(([kind]) => kind === 'ask'), false);
    f.get('payload').open = false; f.get('payload').dispatchEvent(new Event('toggle'));
    await new Promise((resolve) => setImmediate(resolve));
    assert.equal(f.calls.filter(([kind]) => kind === 'aiPayload').length, 1);
  } finally { f.restore(); }
});
test('a truncated retained payload is labelled honestly instead of silently shortened', async () => {
  const f = await fixture();
  try {
    f.get('request').value = 'house'; f.get('request').dispatchEvent(new Event('input'));
    await f.controller.prepare();
    f.controller.payload = { previewId: uuid, surface: 'library', recipient: AI_RECIPIENT, request: 'house', body: '{"a":1}', bytes: 99999, truncated: true };
    f.render();
    assert.match(f.get('payload-hint').textContent, /truncad/i);
    assert.equal(f.get('payload-body').textContent, '{"a":1}');
  } finally { f.restore(); }
});
