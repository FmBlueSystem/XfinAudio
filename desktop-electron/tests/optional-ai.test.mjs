import assert from 'node:assert/strict';
import test from 'node:test';
import { OptionalAiController, AI_RECIPIENT, AI_CONNECTION_REQUEST } from '../.out/renderer/optional-ai.js';
const uuid = '12345678-1234-4123-8123-123456789012';
const status = (patch = {}) => ({ revision: 'a'.repeat(64), enabled: true, provider: 'nan', credentialLabel: 'apiIA.env', configured: true, recipient: AI_RECIPIENT, ...patch });
const preview = (patch = {}) => ({ previewId: uuid, surface: 'library', recipient: AI_RECIPIENT, disclosure: ['Se enviará la petición y el vocabulario de géneros. No se envía audio.'], requestPreview: 'Busca house [ruta omitida]', ...patch });
const result = (patch = {}) => ({ resultId: uuid, surface: 'library', kind: 'filters', title: 'Filtros sugeridos', text: 'Propuesta pendiente de revisión local', proposal: { genres: ['house'] }, canApply: true, ...patch });
function fixture(overrides = {}) {
  const payloadFixture = () => ({ previewId: uuid, surface: 'library', recipient: AI_RECIPIENT, request: 'Busca house', body: payloadBody, bytes: payloadBody.length, truncated: false });
  const calls = []; const applied = []; const dirty = []; let available = true; let busy = false; let route = 0;
  const api = { getAiStatus: async () => { calls.push(['status']); return status(); }, saveAiSettings: async (input) => { calls.push(['save', input]); return status({ ...input, revision: 'b'.repeat(64) }); }, chooseAiCredential: async (input) => { calls.push(['choose', input]); return status({ credentialLabel: 'seleccionado.env', revision: 'b'.repeat(64) }); }, clearAiCredential: async (input) => { calls.push(['clear', input]); return status({ credentialLabel: null, configured: false, revision: 'b'.repeat(64) }); }, prepareAiRequest: async (input) => { calls.push(['prepare', input]); return preview({ surface: input.surface }); }, runAiRequest: async (input) => { calls.push(['run', input]); return { cancelled: false, result: result() }; }, applyAiSuggestion: async (input) => { calls.push(['apply', input]); return { surface: 'library', data: { genres: ['house'] } }; }, inspectAiPayload: async (input) => { calls.push(['payload', input]); return payloadFixture(); }, ...overrides };
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
  const f = fixture(); await prepared(f); f.controller.setConsent(true); f.controller.setContext('library', {}, 'library-1'); assert.equal(f.controller.consent, true); f.controller.setRequest('Otra petición'); assert.equal(f.controller.preview, null); assert.equal(f.controller.consent, false); await f.controller.prepare(); f.controller.setConsent(true); f.controller.setEnabled(false); assert.equal(f.controller.preview, null); f.controller.discard(); f.controller.setContext('library', {}, 'library-2'); assert.equal(f.controller.request, 'Otra petición'); assert.equal(f.controller.preview, null); assert.equal(f.controller.result, null);
});
test('source changes suppress a late prepared preview and a late remote result', async () => {
  let finish; const f = fixture({ prepareAiRequest: () => new Promise((resolve) => { finish = resolve; }) }); await f.controller.load(); f.controller.setRequest('House'); const pending = f.controller.prepare(); f.controller.setContext('library', {}, 'new'); finish(preview()); await pending; assert.equal(f.controller.preview, null);
  const g = fixture({ runAiRequest: () => new Promise((resolve) => { finish = resolve; }) }); await prepared(g); g.controller.setConsent(true); const running = g.controller.ask(); g.controller.setContext('editor', { editId: uuid }, 'editor-1'); finish({ cancelled: false, result: result() }); await running; assert.equal(g.controller.result, null); assert.equal(g.controller.consent, false);
});
test('cancellation cannot recall sent data and prevents any late result after navigation or disconnect', async () => {
  let finish; let runs = 0; const f = fixture({ runAiRequest: () => { runs++; return new Promise((resolve) => { finish = resolve; }); } }); await prepared(f); f.controller.setConsent(true); const running = f.controller.ask(); await f.controller.ask(); f.controller.cancelPending(); f.leave(); finish({ cancelled: false, result: result() }); await running; assert.equal(runs, 1); assert.equal(f.controller.result, null); assert.match(f.controller.notice, /enviados.*recuperar/); assert.equal(f.controller.consent, false);
  const g = fixture({ runAiRequest: () => new Promise((resolve) => { finish = resolve; }) }); await prepared(g); g.controller.setConsent(true); const work = g.controller.ask(); g.offline(); finish({ cancelled: false, result: result() }); await work; assert.equal(g.controller.result, null); assert.equal(g.controller.canAsk, false);
});
test('native confirmation cancellation keeps the prepared disclosure and only removes the per-request consent', async () => {
  let runs = 0; const f = fixture({ runAiRequest: async () => { runs += 1; return { cancelled: true, result: null }; } });
  await prepared(f); f.controller.setConsent(true); const preparedPreview = f.controller.preview;
  await f.controller.ask();
  assert.equal(runs, 1);
  assert.equal(f.controller.preview, preparedPreview);
  assert.equal(f.controller.result, null); assert.equal(f.controller.consent, false); assert.equal(f.controller.pending, null);
  assert.equal(f.controller.notice, 'Envío cancelado: la vista previa sigue disponible; vuelve a marcar la autorización para reintentar.');
  assert.equal(f.controller.canAsk, false);
  f.controller.setConsent(true);
  assert.equal(f.controller.canAsk, true); assert.equal(f.controller.preview, preparedPreview); assert.equal(runs, 1);
});
test('a same-surface refresh keeps the typed instruction while a surface change or a non-editable surface clears it', async () => {
  const f = fixture(); await f.controller.load();
  f.controller.setContext('library', {}, 'library-1'); f.controller.setRequest('Busca house sin ruta');
  f.controller.setContext('library', {}, 'library-2');
  assert.equal(f.controller.request, 'Busca house sin ruta'); assert.equal(f.controller.preview, null); assert.equal(f.controller.result, null); assert.equal(f.controller.consent, false);
  f.controller.setContext('prep', {}, 'prep-1');
  assert.equal(f.controller.request, '');
  f.controller.setRequest('Prepara una sesión house'); f.controller.setContext('metadata', {}, 'metadata-1');
  assert.equal(f.controller.request, '');
  f.controller.setContext('connection', {}, 'connection-1'); assert.equal(f.controller.request, AI_CONNECTION_REQUEST);
  f.controller.setContext('connection', {}, 'connection-2'); assert.equal(f.controller.request, AI_CONNECTION_REQUEST);
  const editor = fixture(); await editor.controller.load();
  editor.controller.setContext('editor', { editId: uuid, draftIds, includeReplacements: false }, 'editor-1');
  editor.controller.setRequest('Mejora el orden');
  editor.controller.setContext('editor', { editId: uuid, draftIds, includeReplacements: true }, 'editor-1');
  assert.equal(editor.controller.request, 'Mejora el orden'); assert.equal(editor.controller.improvementEditor, true); assert.equal(editor.controller.includeReplacements, true);
});
test('invalidating a prepared disclosure with a context refresh raises a Spanish review reminder only when one existed', async () => {
  const f = fixture(); await f.controller.load();
  assert.equal(f.controller.notice, '');
  f.controller.setContext('library', {}, 'library-2'); assert.equal(f.controller.notice, '');
  f.controller.setRequest('Busca house'); await f.controller.prepare(); assert.ok(f.controller.preview);
  f.controller.setContext('library', {}, 'library-3');
  assert.equal(f.controller.preview, null); assert.equal(f.controller.consent, false);
  assert.equal(f.controller.notice, 'Contexto actualizado: revisa la vista previa antes de enviar.');
  const g = fixture(); await g.controller.load(); g.controller.setRequest('Busca house'); await g.controller.prepare(); g.controller.setConsent(true);
  g.controller.setContext('library', {}, 'library-2');
  assert.equal(g.controller.consent, false);
  assert.equal(g.controller.notice, 'Contexto actualizado: revisa la vista previa antes de enviar.');
});
test('improvement validation failures surface specific retry guidance instead of a generic message', async () => {
  const f = fixture({ runAiRequest: async () => { throw new Error('[invalid_improvement] private backend detail'); } });
  await prepared(f); f.controller.setConsent(true); await f.controller.ask();
  assert.match(f.controller.error, /playlist actual/); assert.match(f.controller.error, /borrador/);
  assert.doesNotMatch(f.controller.error, /invalid_improvement|private backend/);
  const g = fixture({ prepareAiRequest: async () => { throw new Error('[ai_context_too_large] private backend detail'); } });
  await g.controller.load(); g.controller.setRequest('Busca house'); await g.controller.prepare();
  assert.match(g.controller.error, /límite/);
  assert.notEqual(g.controller.error, f.controller.error);
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

// --- I3 U3: editor improvement context, kind, and local improvement preview bounds ---
const draftIds = ['a'.repeat(64), 'b'.repeat(64), 'c'.repeat(64)];
const improvementResult = (patch = {}) => ({ resultId: uuid, surface: 'editor', kind: 'improvement', title: 'Mejora propuesta', text: 'Revisa el orden y su evaluación local antes de aplicarlo.', proposal: { orderedTrackIds: ['a1b2c3d4e5f60718'], rationale: 'Menos saltos de energía' }, canApply: true, ...patch });
const pitchedTrack = (index) => ({ id: index.toString(16).padStart(64, '0'), title: `Pista ${index} ${'x'.repeat(200)}`, artist: `Artista ${index}`, bpm: 120, key: '8A', energy: 5, duration: 240, missing: false, missingFields: ['bpm'] });
const largeImprovementPreview = () => {
  const before = Array.from({ length: 80 }, (_, index) => pitchedTrack(index));
  return { editId: uuid, sourceRevision: 'r1', proposalId: uuid, digest: 'c'.repeat(64), before, after: before.map((track) => ({ ...track })), assessment: { description: 'Orden con mejor flujo', readiness: 'ready', qualityScore: 0.7, warnings: ['Transición justa'] }, addedIds: [], removedIds: [] };
};
const improvementFixture = (overrides = {}) => fixture({
  runAiRequest: async () => ({ cancelled: false, result: improvementResult() }),
  applyAiSuggestion: async () => ({ surface: 'editor', data: largeImprovementPreview() }),
  ...overrides,
});
async function improvementReady(overrides = {}) {
  const f = improvementFixture(overrides); await f.controller.load();
  f.controller.setContext('editor', { editId: uuid, draftIds, includeReplacements: false }, 'editor-1');
  f.controller.setRequest('Mejorar esta playlist'); await f.controller.prepare(); f.controller.setConsent(true); await f.controller.ask();
  return f;
}
test('editor improvement context is exact, keeps the legacy editId selector, and binds each selector to its own kind', async () => {
  const f = improvementFixture(); await f.controller.load();
  f.controller.setContext('editor', { editId: uuid, draftIds, includeReplacements: false }, 'editor-1');
  assert.equal(f.controller.improvementEditor, true);
  f.controller.setRequest('Mejorar esta playlist'); await f.controller.prepare();
  assert.deepEqual(f.calls.at(-1), ['prepare', { surface: 'editor', request: 'Mejorar esta playlist', context: { editId: uuid, draftIds, includeReplacements: false } }]);
  const legacy = improvementFixture(); await legacy.controller.load();
  legacy.controller.setContext('editor', { editId: uuid }, 'editor-2'); assert.equal(legacy.controller.improvementEditor, false);
  legacy.controller.setRequest('Añade una intro'); await legacy.controller.prepare();
  assert.deepEqual(legacy.calls.at(-1)[1].context, { editId: uuid });
  const wrong = improvementFixture({ runAiRequest: async () => ({ cancelled: false, result: improvementResult({ kind: 'editor_request', proposal: { request: 'remove' } }) }) });
  await wrong.controller.load(); wrong.controller.setContext('editor', { editId: uuid, draftIds, includeReplacements: false }, 'e'); wrong.controller.setRequest('Mejorar'); await wrong.controller.prepare(); wrong.controller.setConsent(true); await wrong.controller.ask();
  assert.equal(wrong.controller.result, null); assert.ok(wrong.controller.error);
  const legacyWrong = improvementFixture();
  await legacyWrong.controller.load(); legacyWrong.controller.setContext('editor', { editId: uuid }, 'e'); legacyWrong.controller.setRequest('Añade'); await legacyWrong.controller.prepare(); legacyWrong.controller.setConsent(true); await legacyWrong.controller.ask();
  assert.equal(legacyWrong.controller.result, null); assert.ok(legacyWrong.controller.error);
});
test('a partial or malformed editor improvement selector is refused instead of guessed', async () => {
  const f = improvementFixture(); await f.controller.load();
  const cases = [
    { editId: uuid, draftIds },
    { editId: uuid, draftIds, includeReplacements: 'false' },
    { editId: uuid, draftIds: [draftIds[0], draftIds[0]], includeReplacements: false },
    { editId: uuid, draftIds: [draftIds[0]], includeReplacements: false },
    { editId: uuid, draftIds: Array.from({ length: 81 }, (_, index) => index.toString(16).padStart(64, 'a')), includeReplacements: false },
    { editId: uuid, draftIds: [draftIds[0], '/etc/passwd'], includeReplacements: false },
  ];
  for (const context of cases) { f.controller.setContext('editor', context, 'editor-x'); assert.equal(f.controller.improvementEditor, false); assert.equal(f.controller.canPrepare, false); assert.ok(f.controller.error); }
});
test('local improvement apply admits a realistic preview above the legacy bound while the legacy editor stays bounded', async () => {
  const payload = largeImprovementPreview(); const size = JSON.stringify(payload).length;
  assert.ok(size > 32000 && size < 512 * 1024, `unexpected fixture size ${size}`);
  const f = await improvementReady({ applyAiSuggestion: async () => ({ surface: 'editor', data: payload }) });
  await f.controller.applySuggestion();
  assert.equal(f.applied.length, 1); assert.equal(f.applied[0][0], 'editor'); assert.equal(f.applied[0][1].proposalId, uuid); assert.equal(f.applied[0][1].after.length, 80);
  const legacy = improvementFixture({ runAiRequest: async () => ({ cancelled: false, result: improvementResult({ kind: 'editor_request', proposal: { request: 'remove' } }) }), applyAiSuggestion: async () => ({ surface: 'editor', data: payload }) });
  await legacy.controller.load(); legacy.controller.setContext('editor', { editId: uuid }, 'e'); legacy.controller.setRequest('Añade'); await legacy.controller.prepare(); legacy.controller.setConsent(true); await legacy.controller.ask(); await legacy.controller.applySuggestion();
  assert.equal(legacy.applied.length, 0); assert.ok(legacy.controller.error);
});
test('local improvement apply rejects oversized, deep, dangerous and malformed payloads', async () => {
  let deep = 1; for (let index = 0; index < 8; index += 1) deep = { child: deep };
  const oversized = { warnings: Array.from({ length: 200 }, () => 'x'.repeat(4000)) };
  const dangerous = JSON.parse('{"ok":1,"__proto__":{"polluted":true}}');
  for (const data of [oversized, deep, dangerous, null, [], 'text', 7]) {
    const f = await improvementReady({ applyAiSuggestion: async () => ({ surface: 'editor', data }) });
    await f.controller.applySuggestion();
    assert.equal(f.applied.length, 0, `accepted ${JSON.stringify(data)?.slice(0, 40)}`); assert.ok(f.controller.error);
  }
  assert.equal({}.polluted, undefined);
});
test('the replacement toggle discards prepared disclosure and consent and regenerates the exact context', async () => {
  const f = improvementFixture(); await f.controller.load();
  f.controller.setContext('editor', { editId: uuid, draftIds, includeReplacements: false }, 'editor-1');
  f.controller.setRequest('Mejorar esta playlist'); await f.controller.prepare(); f.controller.setConsent(true);
  assert.equal(f.controller.includeReplacements, false); assert.ok(f.controller.preview); assert.equal(f.controller.consent, true);
  f.controller.setIncludeReplacements(true);
  assert.equal(f.controller.includeReplacements, true); assert.equal(f.controller.preview, null); assert.equal(f.controller.result, null); assert.equal(f.controller.consent, false);
  await f.controller.prepare();
  assert.deepEqual(f.calls.at(-1), ['prepare', { surface: 'editor', request: 'Mejorar esta playlist', context: { editId: uuid, draftIds, includeReplacements: true } }]);
  assert.equal(f.controller.canAsk, false);
  const legacy = improvementFixture(); await legacy.controller.load(); legacy.controller.setContext('editor', { editId: uuid }, 'e');
  legacy.controller.setIncludeReplacements(true); assert.equal(legacy.controller.includeReplacements, false);
});

test('a local improvement review never claims the draft was applied while other surfaces keep that copy', async () => {
  const f = await improvementReady({ applyAiSuggestion: async () => ({ surface: 'editor', data: largeImprovementPreview() }) });
  await f.controller.applySuggestion();
  assert.equal(f.applied.length, 1);
  assert.match(f.controller.notice, /borrador/i);
  assert.doesNotMatch(f.controller.notice, /aplicad[ao] al trabajo local/i);
  const g = fixture(); await prepared(g); g.controller.setConsent(true); await g.controller.ask(); await g.controller.applySuggestion();
  assert.match(g.controller.notice, /aplicada al trabajo local/i);
});

// --- F2/F10: phase-aware pending copy, elapsed helper and prepare blockers ---
test('pendingPhaseText names the current phase while ask exposes a pure elapsed-seconds helper', async () => {
  const f = fixture(); await f.controller.load();
  assert.equal(f.controller.pendingPhaseText, '');
  assert.equal(f.controller.askElapsedSeconds(Date.now()), null);
  f.controller.pending = 'load'; assert.equal(f.controller.pendingPhaseText, 'Consultando ajustes de IA…');
  f.controller.pending = 'prepare'; assert.equal(f.controller.pendingPhaseText, 'Preparando la vista previa de datos…');
  f.controller.pending = 'apply'; assert.equal(f.controller.pendingPhaseText, 'Revisando la propuesta con el motor local…');
  f.controller.pending = 'save'; assert.equal(f.controller.pendingPhaseText, 'Guardando ajustes de IA…');
  f.controller.pending = 'choose'; assert.equal(f.controller.pendingPhaseText, 'Elige el archivo de credenciales en el sistema');
  f.controller.pending = 'clear'; assert.equal(f.controller.pendingPhaseText, 'Quitando fuente de credenciales…');
  f.controller.pending = 'ask'; assert.equal(f.controller.pendingPhaseText, 'Consultando a Nan Builders… puede tardar hasta 30 s');
  const now = Date.now(); f.controller.askStartedAt = now - 12000;
  assert.equal(f.controller.askElapsedSeconds(now), 12);
  assert.equal(f.controller.askElapsedSeconds(now - 12000), 0);
  f.controller.pending = null; f.controller.askStartedAt = null;
  assert.equal(f.controller.pendingPhaseText, ''); assert.equal(f.controller.askElapsedSeconds(now), null);
});
test('prepareBlocker returns the first failing reason in user order and is empty only when preparation is possible', async () => {
  const enabled = fixture(); await enabled.controller.load(); enabled.controller.setRequest('Busca house');
  assert.equal(enabled.controller.canPrepare, true); assert.equal(enabled.controller.prepareBlocker(), '');
  enabled.controller.setEnabled(false); assert.equal(enabled.controller.prepareBlocker(), 'Activa la asistencia IA en Ajustes.');
  enabled.controller.surface = 'connection';
  assert.equal(enabled.controller.prepareBlocker(), 'Activa la asistencia IA en «Ajustes de asistencia IA».');
  enabled.controller.surface = 'editor';
  const unconfigured = fixture({ getAiStatus: async () => status({ configured: false, credentialLabel: null }) }); await unconfigured.controller.load(); unconfigured.controller.setRequest('Busca house');
  assert.equal(unconfigured.controller.prepareBlocker(), 'Selecciona una fuente de credenciales en Ajustes.');
  const dirty = fixture({ getAiStatus: async () => status({ enabled: false }) }); await dirty.controller.load(); dirty.controller.setEnabled(true); dirty.controller.setRequest('Busca house');
  assert.equal(dirty.controller.prepareBlocker(), 'Guarda o descarta los cambios de IA pendientes.');
  const pending = fixture(); await pending.controller.load(); pending.controller.setRequest('Busca house'); pending.controller.pending = 'prepare';
  assert.equal(pending.controller.prepareBlocker(), 'Hay una operación local en curso.');
  pending.controller.pending = 'ask';
  assert.equal(pending.controller.prepareBlocker(), 'Hay una consulta a la IA en curso.');
  const stale = fixture(); await stale.controller.load(); stale.controller.setRequest('Busca house'); stale.controller.invalidate();
  assert.equal(stale.controller.prepareBlocker(), 'Abre la selección o pantalla de origen de nuevo.');
  const empty = fixture(); await empty.controller.load();
  assert.equal(empty.controller.prepareBlocker(), 'Escribe qué quieres mejorar.');
  const oversized = fixture(); await oversized.controller.load(); oversized.controller.setRequest('x'.repeat(2001));
  assert.equal(oversized.controller.prepareBlocker(), 'La petición supera los 2000 caracteres.');
});

// --- F6: provider-free exact payload inspection, on demand only ---------------
const payloadBody = '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"{\\"request\\":\\"Busca house\\"}"}]}';
const aiPayload = (patch = {}) => ({ previewId: uuid, surface: 'library', recipient: AI_RECIPIENT, request: 'Busca house', body: payloadBody, bytes: payloadBody.length, truncated: false, ...patch });
test('payload inspection is on demand, read-only, never automatic and cleared by any context change', async () => {
  const f = fixture(); await prepared(f);
  assert.equal(f.controller.payload, null);
  assert.ok(!f.calls.some(([kind]) => kind === 'payload'));
  assert.equal(f.controller.canInspectPayload, true);
  await f.controller.inspectPayload();
  assert.deepEqual(f.calls.at(-1), ['payload', { previewId: uuid }]);
  assert.equal(f.controller.payload.body, payloadBody);
  assert.equal(f.controller.payload.truncated, false);
  assert.equal(f.controller.preview.previewId, uuid);
  assert.ok(!f.calls.some(([kind]) => kind === 'run' || kind === 'apply'));
  f.controller.setRequest('Otra petición');
  assert.equal(f.controller.payload, null);
  assert.equal(f.controller.canInspectPayload, false);
  await f.controller.inspectPayload();
  assert.equal(f.calls.filter(([kind]) => kind === 'payload').length, 1);
  // A sent request leaves no inspectable body behind, and its consent is revoked.
  f.controller.setRequest('Busca house'); await f.controller.prepare(); await f.controller.inspectPayload();
  f.controller.setConsent(true); await f.controller.ask();
  assert.equal(f.controller.preview, null); assert.equal(f.controller.payload, null); assert.equal(f.controller.canInspectPayload, false);
});
test('a foreign, malformed or out-of-bounds payload response is refused and never retained', async () => {
  const patches = [{ previewId: '00000000-0000-4000-8000-000000000000' }, { body: 1 }, { body: 'x'.repeat(64 * 1024 + 1) }, { truncated: 'no' }, { bytes: -1 }, { request: 7 }, { recipient: 'https://elsewhere.example' }, null];
  for (const patch of patches) {
    const f = fixture({ inspectAiPayload: async () => (patch === null ? null : aiPayload(patch)) });
    await prepared(f);
    await f.controller.inspectPayload();
    assert.equal(f.controller.payload, null, JSON.stringify(patch)?.slice(0, 60));
    assert.notEqual(f.controller.error, '', JSON.stringify(patch)?.slice(0, 60));
  }
});
test('an offline host cannot inspect a payload even when a preview is prepared', async () => {
  const f = fixture(); await prepared(f); assert.equal(f.controller.canInspectPayload, true);
  f.offline();
  assert.equal(f.controller.canInspectPayload, false);
  await f.controller.inspectPayload();
  assert.ok(!f.calls.some(([kind]) => kind === 'payload'));
});

// --- Mid-flight instruction edits must not destroy a paid, consented provider response ---
test('a keystroke during the in-flight ask cannot discard the sent request, its disclosure or its result', async () => {
  let finish; let runs = 0;
  const f = fixture({ runAiRequest: () => { runs += 1; return new Promise((resolve) => { finish = resolve; }); } });
  await prepared(f);
  const previewBefore = f.controller.preview;
  f.controller.setConsent(true);
  const running = f.controller.ask();
  assert.equal(f.controller.pending, 'ask');
  f.controller.setRequest('Otra petición distinta');
  assert.equal(f.controller.request, 'Busca house /Users/private', 'the instruction bound to the sent request must stay authoritative');
  assert.equal(f.controller.preview, previewBefore);
  finish({ cancelled: false, result: result() });
  await running;
  assert.ok(f.controller.result, 'the paid provider result must survive a mid-flight keystroke');
  assert.equal(f.controller.result.kind, 'filters');
  assert.equal(f.controller.consent, false, 'the one-shot consent is still consumed exactly once');
  assert.equal(f.controller.pending, null);
  assert.equal(runs, 1, 'no silent re-send');
});

test('a keystroke during the in-flight ask does not silently swallow a provider failure either', async () => {
  let reject; const f = fixture({ runAiRequest: () => new Promise((_resolve, fail) => { reject = fail; }) });
  await prepared(f); f.controller.setConsent(true);
  const running = f.controller.ask();
  f.controller.setRequest('Otra petición distinta');
  reject(new Error('provider exploded'));
  await running;
  // The controller normalizes provider detail into one bounded message; what matters is that the
  // failure stays reported instead of being erased by the reset a mid-flight edit used to trigger.
  assert.notEqual(f.controller.error, '', 'the failure stays visible instead of being swallowed by a reset');
  assert.equal(f.controller.pending, null);
  assert.equal(f.calls.filter(([kind]) => kind === 'run').length, 0);
});
