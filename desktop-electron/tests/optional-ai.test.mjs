import assert from 'node:assert/strict';
import test from 'node:test';
import { OptionalAiController, AI_RECIPIENT } from '../.out/renderer/optional-ai.js';
const uuid = '12345678-1234-4123-8123-123456789012';
const status = (patch = {}) => ({ revision: 'a'.repeat(64), enabled: true, provider: 'nan', credentialLabel: 'apiIA.env', configured: true, recipient: AI_RECIPIENT, ...patch });
const preview = (patch = {}) => ({ previewId: uuid, surface: 'library', recipient: AI_RECIPIENT, disclosure: ['Se enviará la petición y el vocabulario de géneros. No se envía audio.'], requestPreview: 'Busca house [ruta omitida]', ...patch });
const result = (patch = {}) => ({ resultId: uuid, surface: 'library', kind: 'filters', title: 'Filtros sugeridos', text: 'Propuesta pendiente de revisión local', proposal: { genres: ['house'] }, canApply: true, ...patch });
function fixture(overrides = {}) {
  const calls = []; const applied = []; const dirty = []; let available = true; let busy = false; let route = 0;
  const api = { getAiStatus: async () => { calls.push(['status']); return status(); }, saveAiSettings: async (input) => { calls.push(['save', input]); return status({ ...input, revision: 'b'.repeat(64) }); }, chooseAiCredential: async (input) => { calls.push(['choose', input]); return status({ credentialLabel: 'seleccionado.env', revision: 'b'.repeat(64) }); }, clearAiCredential: async (input) => { calls.push(['clear', input]); return status({ credentialLabel: null, configured: false, revision: 'b'.repeat(64) }); }, prepareAiRequest: async (input) => { calls.push(['prepare', input]); return preview({ surface: input.surface }); }, runAiRequest: async (input) => { calls.push(['run', input]); return { cancelled: false, result: result() }; }, applyAiSuggestion: async (input) => { calls.push(['apply', input]); return { surface: 'library', data: { genres: ['house'] } }; }, ...overrides };
  const controller = new OptionalAiController(api, { canAct: () => available && !busy, changed: () => {}, dirtyChanged: (value) => dirty.push(value), applied: (surface, data) => applied.push([surface, data]), perform: async (_label, task, apply, fail) => { busy = true; const current = route; try { apply(await task(), current === route); } catch (error) { fail(error); } finally { busy = false; } } });
  controller.setContext('library', {}, 'library-1');
  return { controller, calls, applied, dirty, leave: () => { route++; }, offline: () => { available = false; controller.invalidate(); } };
}
async function prepared(f) { await f.controller.load(); f.controller.setRequest('Busca house /Users/private'); await f.controller.prepare(); }
test('status and configuration are local only, dirty draft survives navigation until save or discard', async () => {
  const f = fixture(); await f.controller.load(); assert.deepEqual(f.calls, [['status']]); f.controller.setEnabled(false); assert.equal(f.controller.dirty, true); f.leave(); await f.controller.load(); assert.equal(f.calls.length, 1); assert.match(f.controller.error, /descarta/i); f.controller.discard(); assert.equal(f.controller.snapshot.enabled, true); assert.equal(f.controller.dirty, false); f.controller.setEnabled(false); await f.controller.save(); assert.deepEqual(f.calls.at(-1), ['save', { revision: 'a'.repeat(64), enabled: false }]); assert.equal(f.controller.dirty, false); assert.equal(f.applied.length, 0);
});
test('credential source picker and removal use only current revision and never request provider data', async () => {
  const f = fixture(); await f.controller.load(); await f.controller.chooseCredential(); assert.deepEqual(f.calls.at(-1), ['choose', { revision: 'a'.repeat(64) }]); assert.equal(f.controller.snapshot.credentialLabel, 'seleccionado.env'); await f.controller.clearCredential(); assert.deepEqual(f.calls.at(-1), ['clear', { revision: 'b'.repeat(64) }]); assert.equal(f.controller.snapshot.configured, false); assert.equal(f.controller.canPrepare, false); assert.ok(!f.calls.some(([kind]) => kind === 'run'));
});
test('readonly preparation precedes unchecked consent and ask sends only the opaque preview ID', async () => {
  const f = fixture(); await prepared(f); assert.equal(f.controller.consent, false); assert.equal(f.controller.preview.requestPreview, 'Busca house [ruta omitida]'); assert.equal(f.controller.canAsk, false); await f.controller.ask(); assert.ok(!f.calls.some(([kind]) => kind === 'run')); f.controller.setConsent(true); assert.equal(f.controller.canAsk, true); await f.controller.ask(); assert.deepEqual(f.calls.at(-1), ['run', { previewId: uuid }]); assert.equal(f.controller.consent, false); assert.equal(f.controller.result.kind, 'filters'); assert.equal(f.applied.length, 0);
});
test('explicit Apply alone invokes local parent integration and cannot be repeated', async () => {
  const f = fixture(); await prepared(f); f.controller.setConsent(true); await f.controller.ask(); await f.controller.applySuggestion(); assert.deepEqual(f.calls.at(-1), ['apply', { resultId: uuid }]); assert.deepEqual(f.applied, [['library', { genres: ['house'] }]]); await f.controller.applySuggestion(); assert.equal(f.applied.length, 1);
});
test('same context keeps the draft while changed source/request/configuration removes consent and stale results', async () => {
  const f = fixture(); await prepared(f); f.controller.setConsent(true); f.controller.setContext('library', {}, 'library-1'); assert.equal(f.controller.consent, true); f.controller.setRequest('Otra petición'); assert.equal(f.controller.preview, null); assert.equal(f.controller.consent, false); await f.controller.prepare(); f.controller.setConsent(true); f.controller.setEnabled(false); assert.equal(f.controller.preview, null); f.controller.discard(); f.controller.setContext('library', {}, 'library-2'); assert.equal(f.controller.request, ''); assert.equal(f.controller.result, null);
});
test('source changes suppress a late prepared preview and a late remote result', async () => {
  let finish; const f = fixture({ prepareAiRequest: () => new Promise((resolve) => { finish = resolve; }) }); await f.controller.load(); f.controller.setRequest('House'); const pending = f.controller.prepare(); f.controller.setContext('library', {}, 'new'); finish(preview()); await pending; assert.equal(f.controller.preview, null);
  const g = fixture({ runAiRequest: () => new Promise((resolve) => { finish = resolve; }) }); await prepared(g); g.controller.setConsent(true); const running = g.controller.ask(); g.controller.setContext('editor', { editId: uuid }, 'editor-1'); finish({ cancelled: false, result: result() }); await running; assert.equal(g.controller.result, null); assert.equal(g.controller.consent, false);
});
test('cancellation cannot recall sent data and prevents any late result after navigation or disconnect', async () => {
  let finish; let runs = 0; const f = fixture({ runAiRequest: () => { runs++; return new Promise((resolve) => { finish = resolve; }); } }); await prepared(f); f.controller.setConsent(true); const running = f.controller.ask(); await f.controller.ask(); f.controller.cancelPending(); f.leave(); finish({ cancelled: false, result: result() }); await running; assert.equal(runs, 1); assert.equal(f.controller.result, null); assert.match(f.controller.notice, /enviados.*recuperar/); assert.equal(f.controller.consent, false);
  const g = fixture({ runAiRequest: () => new Promise((resolve) => { finish = resolve; }) }); await prepared(g); g.controller.setConsent(true); const work = g.controller.ask(); g.offline(); finish({ cancelled: false, result: result() }); await work; assert.equal(g.controller.result, null); assert.equal(g.controller.canAsk, false);
});
test('native confirmation cancellation creates no result and a new request needs new preview and consent', async () => {
  const f = fixture({ runAiRequest: async () => ({ cancelled: true, result: null }) }); await prepared(f); f.controller.setConsent(true); await f.controller.ask(); assert.equal(f.controller.result, null); assert.equal(f.controller.preview, null); assert.equal(f.controller.consent, false); assert.match(f.controller.notice, /cancelada/i);
});
test('commentary and connection output cannot be applied even if a response claims otherwise', async () => {
  for (const surface of ['review', 'metadata', 'live', 'connection']) { const kind = surface === 'connection' ? 'connection' : 'commentary'; const f = fixture({ runAiRequest: async () => ({ cancelled: false, result: result({ surface, kind, canApply: true }) }) }); await f.controller.load(); f.controller.setContext(surface, surface === 'review' ? { reviewId: uuid } : surface === 'live' ? { sessionId: uuid, revision: 0 } : {}, surface); await f.controller.prepare(); f.controller.setConsent(true); await f.controller.ask(); assert.equal(f.controller.canApply, false); await f.controller.applySuggestion(); assert.equal(f.applied.length, 0); }
});
test('synthetic connection test follows the same explicit preview and consent with empty context', async () => {
  const f = fixture(); await f.controller.load(); f.controller.setContext('connection', {}, 'test'); assert.ok(f.controller.request); await f.controller.prepare(); assert.deepEqual(f.calls.at(-1)[1].context, {}); assert.equal(f.calls.at(-1)[1].surface, 'connection'); assert.equal(f.controller.consent, false); assert.ok(!f.calls.some(([kind]) => kind === 'run'));
});
test('disabled/unconfigured state, invalid request or dirty settings cannot prepare a provider request', async () => {
  for (const patch of [{ enabled: false }, { configured: false, credentialLabel: null }]) { const f = fixture({ getAiStatus: async () => status(patch) }); await f.controller.load(); f.controller.setRequest('House'); await f.controller.prepare(); assert.equal(f.calls.length, 0); assert.equal(f.controller.canPrepare, false); }
  const f = fixture(); await f.controller.load(); f.controller.setRequest('x'.repeat(2001)); await f.controller.prepare(); assert.equal(f.controller.canPrepare, false); f.controller.setRequest('House'); f.controller.setEnabled(false); assert.equal(f.controller.canPrepare, false);
});
test('stale config save preserves enabled draft and errors never expose credential paths or provider internals', async () => {
  const f = fixture({ saveAiSettings: async () => { throw new Error('[stale_settings] /Users/private/apiIA.env'); } }); await f.controller.load(); f.controller.setEnabled(false); await f.controller.save(); assert.equal(f.controller.dirty, true); assert.equal(f.controller.canSave, false); assert.match(f.controller.error, /descarta.*actualiza/i); assert.doesNotMatch(f.controller.error, /Users|apiIA/);
  const g = fixture({ prepareAiRequest: async () => { throw new Error('Bearer secret /private'); } }); await prepared(g); assert.doesNotMatch(g.controller.error, /Bearer|secret|private/); assert.equal(g.controller.preview, null);
});
test('unexpected recipient, mismatched surface and malformed apply cannot reach parent or consent', async () => {
  const f = fixture({ prepareAiRequest: async () => preview({ recipient: 'https://attacker.invalid' }) }); await prepared(f); assert.equal(f.controller.preview, null); assert.ok(f.controller.error);
  const g = fixture({ runAiRequest: async () => ({ cancelled: false, result: result({ surface: 'editor' }) }) }); await prepared(g); g.controller.setConsent(true); await g.controller.ask(); assert.equal(g.controller.result, null);
  const h = fixture({ applyAiSuggestion: async () => ({ surface: 'editor', data: {} }) }); await prepared(h); h.controller.setConsent(true); await h.controller.ask(); await h.controller.applySuggestion(); assert.equal(h.applied.length, 0);
});
test('credential source changes refuse a dirty enabled draft without opening the picker', async () => {
  const f = fixture(); await f.controller.load(); f.controller.setEnabled(false); await f.controller.chooseCredential(); await f.controller.clearCredential(); assert.deepEqual(f.calls, [['status']]); assert.equal(f.controller.snapshot.enabled, false); assert.equal(f.controller.dirty, true); assert.match(f.controller.error, /Guarda o descarta/);
});
test('context schemas reject paths, unsupported surfaces and oversize sources before preparation', async () => {
  const f = fixture(); await f.controller.load();
  for (const [surface, context] of [['library', { path: '/private' }], ['review', { reviewId: 'bad' }], ['live', { sessionId: uuid, revision: 501 }], ['saved', { playlistIds: Array.from({ length: 201 }, (_, i) => String(i)) }], ['constructor', {}]]) { f.controller.setContext(surface, context, 'next'); f.controller.setRequest('Consulta'); await f.controller.prepare(); assert.equal(f.controller.canPrepare, false, surface); }
  assert.deepEqual(f.calls, [['status']]);
});
test('a late local apply cannot affect a replaced source', async () => {
  let finish; const f = fixture({ applyAiSuggestion: () => new Promise((resolve) => { finish = resolve; }) }); await prepared(f); f.controller.setConsent(true); await f.controller.ask(); const work = f.controller.applySuggestion(); f.controller.setContext('prep', {}, 'changed'); finish({ surface: 'library', data: { genres: ['house'] } }); await work; assert.equal(f.applied.length, 0); assert.equal(f.controller.result, null);
});
test('trusted local library Apply admits up to100000 opaque IDs without expanding provider proposal limits', async () => {
  const ids=Array.from({length:100000},(_,i)=>i.toString(16).padStart(64,'0')); const f=fixture({applyAiSuggestion:async()=>({surface:'library',data:{filters:{genres:['house']},trackIds:ids}})}); await prepared(f); f.controller.setConsent(true); await f.controller.ask(); await f.controller.applySuggestion(); assert.equal(f.applied[0]?.[1].trackIds.length,100000);
  const g=fixture({runAiRequest:async()=>({cancelled:false,result:result({proposal:{trackIds:ids}})})}); await prepared(g);g.controller.setConsent(true);await g.controller.ask();assert.equal(g.controller.result,null);
});
test('oversized trusted local filter is refused rather than silently truncated',async()=>{const f=fixture({applyAiSuggestion:async()=>({surface:'library',data:{filters:{},trackIds:Array(100001).fill('a'.repeat(64))}})});await prepared(f);f.controller.setConsent(true);await f.controller.ask();await f.controller.applySuggestion();assert.equal(f.applied.length,0);assert.ok(f.controller.error);});
