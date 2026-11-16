import assert from 'node:assert/strict';
import test from 'node:test';
class Element extends EventTarget {
  constructor(tag = 'div') { super(); this.tagName = tag; }
  textContent = ''; value = ''; checked = false; disabled = false; hidden = false; dataset = {}; children = []; attrs = {}; classes = new Set(); paused = true; duration = 0; currentTime = 0;
  get options() { return this.children; } get selectedOptions() { return this.children.filter(node=>node.selected); }
  classList = { toggle: (key, active) => active ? this.classes.add(key) : this.classes.delete(key), contains: (key) => this.classes.has(key) };
  setAttribute(key, value) { this.attrs[key] = value; } removeAttribute(key) { delete this.attrs[key]; }
  append(...nodes) { this.children.push(...nodes); } replaceChildren(...nodes) { this.children = nodes; } closest() { return null; } focus() { this.focused = true; } pause() { this.paused = true; } load() {} async play() { this.paused = false; }
}
const all = (node) => [node, ...node.children.flatMap(all)]; const text = (node) => [node.textContent, ...node.children.map(text)].join(' ');
const tick = () => new Promise((resolve) => setImmediate(resolve)); const settle = async () => { for (let i = 0; i < 5; i++) await tick(); };
const prefs = (patch = {}) => ({ revision: 'a'.repeat(64), previewVolume: .25, watchLibrary: true, recoveryWarning: false, libraryLabels: ['DJ'], capabilities: { loudnessWriteback: false, providers: false, language: 'es' }, ...patch });
const status = (patch = {}) => ({ revision: 1, changeState: 'restored', watchState: 'active', rootCount: 1, watchedCount: 1, ...patch });
const tracks = ['a', 'b'].map((id) => ({ id: id.repeat(64), title: id, artist: 'DJ', bpm: 120, key: '8A', energy: 5, duration: 120, missing: false }));
const loudness = (patch = {}) => ({ revision: 'a'.repeat(64), enabled: true, targetLufs: -10, toleranceLu: 2, available: true, reason: 'ready', totalTracks: tracks.length, tracks: tracks.map((track) => ({ track, state: 'unmeasured', complete: false, lufs: null, lra: null, truePeak: null })), ...patch });
const receipt = (patch = {}) => ({ cancelled: false, changedCount: 1, unchangedCount: 1, failureCount: 0, backupCount: 1, status: loudness(), ...patch });
const aiUuid = '12345678-1234-4123-8123-123456789012';
const aiStatus = { revision: 'c'.repeat(64), enabled: true, provider: 'nan', autoAuthorize: false, configured: true, credentialLabel: 'dummy.env', recipient: 'https://api.nan.builders/v1/chat/completions' };
let sequence = 0;
async function fixture(overrides = {}) {
  const previousDocument = globalThis.document; const previousWindow = globalThis.window; const elements = new Map(); const calls = []; let onStatus; let progress; let statusUnsubscribed = false;
  const nodes = () => [...elements.values()].flatMap(all); const get = (id) => { const dynamic = nodes().find((node) => node.id === id); if (dynamic) return dynamic; if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  const routes = ['library', 'preferences', 'loudness', 'ai', 'prep', 'metadata', 'playlists', 'editor', 'review', 'live', 'serato'].map((route) => { const button = new Element('button'); button.dataset.route = route; return button; });
  let aiSurface = 'library'; const aiKinds = { library:'filters', prep:'intent', editor:'editor_request', saved:'saved_selection', review:'commentary', metadata:'commentary', live:'commentary', connection:'connection', chat:'chat' };
  // The list assistant keeps one conversation in the core: the bridge exposes the two
  // no-param methods the chat panel calls, and a chat turn returns the stored list.
  let chatConversation = [];
  // The pending proposals the fake core holds for this conversation.
  let chatActions = [];
  const api = {
    aiChatHistory: async () => { calls.push(['aiChatHistory']); return { conversation: chatConversation.map((item) => ({ ...item })), actions: chatActions.map((item) => ({ ...item })) }; },
    aiChatReset: async () => { calls.push(['aiChatReset']); chatConversation = []; chatActions = []; return { conversation: [], actions: [] }; },
    aiChatApply: async (input) => { calls.push(['aiChatApply', input]); throw new Error('unreachable'); },
    getAiStatus: async () => { calls.push(['aiStatus']); return aiStatus; }, saveAiSettings: async (input) => { calls.push(['aiSave',input]); return {...aiStatus,...input}; }, chooseAiCredential: async () => aiStatus, clearAiCredential: async () => ({...aiStatus,configured:false,credentialLabel:null}),
    prepareAiRequest: async (input) => { calls.push(['aiPrepare',input]); aiSurface=input.surface; return {previewId:aiUuid,surface:aiSurface,recipient:aiStatus.recipient,disclosure:['Datos autorizados'],requestPreview:input.request,firstTurn:chatConversation.length===0}; },
    inspectAiPayload: async (input) => { calls.push(['aiPayload',input]); return {previewId:aiUuid,surface:aiSurface,recipient:aiStatus.recipient,request:'',body:'{"model":"deepseek","messages":[]}',bytes:31,truncated:false}; },
    runAiRequest: async (input) => { calls.push(['aiRun',input]); if (aiSurface === 'chat') { chatConversation = [...chatConversation, { role: 'user', text: 'Pregunta de la lista' }, { role: 'assistant', text: 'Pista sugerida: la segunda.' }]; return {cancelled:false,result:{resultId:aiUuid,surface:'chat',kind:'chat',title:'Asistente de lista',text:'Pista sugerida: la segunda.',proposal:null,canApply:false,conversation:chatConversation.map((item)=>({...item})),listChanged:true,actions:chatActions.map((item)=>({...item})),droppedActions:0}}; } return {cancelled:false,result:{resultId:aiUuid,surface:aiSurface,kind:aiKinds[aiSurface],title:'Propuesta IA',text:'Revisión local',proposal:{summary:'sugerencia'},canApply:true}}; },
    applyAiSuggestion: async (input) => { calls.push(['aiApply',input]); return {surface:aiSurface,data:aiSurface==='library'?{filters:{genres:['house']},trackIds:[tracks[0].id]}:aiSurface==='prep'?{targetTrackCount:2,name:'Sesión propuesta',targetMinutes:30}:aiSurface==='editor'?{request:'acorta a 2 temas'}:{action:'compare',playlistIds:['1'],comparison:'Comparación local <img src=x>',names:['Set']}}; },
    getLoudnessStatus: async () => { calls.push(['loudness']); return loudness(); },
    saveLoudnessSettings: async (input) => { calls.push(['saveLoudness', input]); return loudness({ ...input, revision: 'b'.repeat(64) }); },
    previewLoudness: async (input) => { calls.push(['previewLoudness', input]); return { previewId: '12345678-1234-4123-8123-123456789012', trackCount: input.trackIds.length, backupBytes: 2048, force: input.force, replaceComments: true, tracks: tracks.filter((track) => input.trackIds.includes(track.id)) }; },
    runLoudness: async (input) => { calls.push(['runLoudness', input]); return receipt(); },
    cancelCurrent: async () => { calls.push(['cancel']); },
    listLibrary: async () => { calls.push(['library']); return { tracks, count: 2 }; }, getPrepCatalog: async () => ({ strategies: [] }), onProgress: (callback) => { progress = callback; return () => {}; },
    getPreferences: async () => { calls.push(['preferences']); return prefs(); }, savePreferences: async (input) => { calls.push(['savePreferences', input]); return prefs({ ...input, revision: 'b'.repeat(64) }); },
    getLibraryStatus: async () => { calls.push(['status']); return status(); }, onLibraryStatus: (callback) => { onStatus = callback; return () => { statusUnsubscribed = true; }; },
    rescanLibrary: async () => { calls.push(['rescan']); return { tracks, count: 2 }; }, setDraftDirty: async (dirty) => { calls.push(['dirty', dirty]); },
    listPlaylists: async () => [{ id: '1', name: 'Set', trackCount: 2, createdAt: '' }], openPlaylistEditor: async () => ({ id: '1', editId: aiUuid, revision: 'r1', name: 'Set', tracks, missingTrackCount: 0 }), discardPlaylistEdit: async () => ({ id: '1', editId: aiUuid, revision: 'r1', name: 'Set', tracks, missingTrackCount: 0 }),
    savePlaylistEdit: async (input) => { calls.push(['saveEdit', input]); return { id: '1', editId: aiUuid, revision: 'r2', name: input.name, tracks, missingTrackCount: 0 }; },
    savePlaylistImprovement: async (input) => { calls.push(['saveImprovement', input]); return { id: '1', editId: aiUuid, revision: 'r2', name: input.name, tracks, missingTrackCount: 0 }; },
    generatePrep: async (input) => { calls.push(['generate', input]); return ({ reviewId: aiUuid, name: 'Set', variant: 'balanced', readiness: 'ready', tracks, warnings: [], blockers: [] }); },
    openLive: async () => ({ sessionId: aiUuid, revision: 0, sourceReviewId: aiUuid, state: 'active', current: tracks[0], history: [], candidates: [{ track: tracks[1], score: 1, alerts: [] }], elapsedSeconds: 0 }),
    chooseSeratoDestination: async () => ({ destinationId: 'dest', label: '_Serato_' }), previewSeratoExport: async () => ({ previewId: 'preview', sourceRevision: 'r', filename: 'Set.crate', destinationLabel: '_Serato_', trackCount: 2, readiness: 'ready', warnings: [], blockers: [], canCommit: true, tracks, backup: { required: false } }), ...overrides,
  };
  globalThis.document = { getElementById: get, createElement: (tag) => new Element(tag), title: '', querySelectorAll: (selector) => selector === '[data-route]' || selector === '.nav-item' ? routes : selector === '[data-mutation]' ? nodes().filter((node) => 'mutation' in node.dataset) : selector === '[data-track-id]' ? nodes().filter((node) => 'trackId' in node.dataset) : [] };
  globalThis.window = Object.assign(new EventTarget(), { xfin: api }); get('metadata-filter').value = 'all'; get('prep-count').value = '2';
  await import(`../.out/renderer/app.js?optionalAiApp=${++sequence}`); await settle();
  const click = (id) => get(id).dispatchEvent(new Event('click')); const navigate = async (route) => { routes.find((button) => button.dataset.route === route).dispatchEvent(new Event('click')); await settle(); };
  return { get, calls, nodes, click, chatActions: (value) => { chatActions = value; }, navigate, openAi: async () => { get('ai-panel').open = true; get('ai-panel').dispatchEvent(new Event('toggle')); await settle(); }, progress: (event) => progress(event), event: (value) => { assert.equal(typeof onStatus, 'function'); onStatus(value); }, offline: () => progress({ operation: 'core', phase: 'error', message: '/private/core' }), statusUnsubscribed: () => statusUnsubscribed, generate: async () => { get('prep-form').dispatchEvent(new Event('submit', { cancelable: true })); await settle(); }, restore: () => { window.dispatchEvent(new Event('beforeunload')); globalThis.document = previousDocument; globalThis.window = previousWindow; } };
}
async function aiReady(f, route = 'library', request = 'Busca house') { await f.navigate(route); await f.openAi(); f.get('optional-ai-request').value = request; f.get('optional-ai-request').dispatchEvent(new Event('input')); f.click('optional-ai-prepare'); await settle(); f.get('optional-ai-consent').checked = true; f.get('optional-ai-consent').dispatchEvent(new Event('change')); }
async function aiResult(f, route = 'library') { await aiReady(f, route); f.click('optional-ai-ask'); await settle(); }
const editorImprovementResult = { resultId: aiUuid, surface: 'editor', kind: 'improvement', title: 'Mejora propuesta', text: 'Revisa el orden local', proposal: { orderedTrackIds: ['a1b2c3d4e5f60718'] }, canApply: true };
const improvementPayload = (patch = {}) => ({ proposalId: 'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee', digest: 'f'.repeat(64), sourceRevision: 'r1', before: tracks.map((track) => ({ ...track })), after: [tracks[1], tracks[0]].map((track) => ({ ...track })), assessment: { description: 'Motor local', readiness: 'needs_review', qualityScore: 0.8, warnings: ['Aviso local'] }, addedIds: [], removedIds: [], ...patch });
const openEditor = async (f) => { await f.navigate('playlists'); f.nodes().find((node) => node.tagName === 'button' && node.textContent === 'Editar').dispatchEvent(new Event('click')); await settle(); };
test('one AI panel loads status only when opened, with dedicated synthetic connection route', async () => {
  const f = await fixture(); try { assert.equal(f.calls.some(([kind]) => kind === 'aiStatus'), false); await f.openAi(); assert.equal(f.calls.filter(([kind]) => kind === 'aiStatus').length, 1); assert.equal(f.calls.some(([kind]) => kind === 'aiRun'), false); await f.navigate('ai'); assert.equal(document.title, 'XfinAudio · IA opcional'); assert.equal(f.get('optional-ai-request-field').hidden, true); f.click('optional-ai-prepare'); await settle(); assert.deepEqual(f.calls.findLast(([kind]) => kind === 'aiPrepare')[1], {surface:'connection',context:{},request:'Reply with OK. XfinAudio connection test.'}); assert.equal(f.get('optional-ai-consent').checked, false); } finally { f.restore(); }
});
test('Prep request survives a local job: editable while busy, explicit wait reason, preview manual only after idle', async () => {
  const report = { totalTracks: 2, completeCount: 2, incompleteCount: 0, gaps: { bpm: 0, camelot_key: 0, energy_level: 0 }, yearCoverage: { withReleaseYear: 0, withoutReleaseYear: 2 }, tracks: [], repairPlan: 'Sin cambios', readOnly: true };
  let finish; const f = await fixture({ getMetadataReport: () => new Promise((resolve) => { finish = resolve; }) });
  try {
    await f.navigate('prep'); await f.openAi();
    assert.equal(f.calls.filter(([kind]) => kind === 'aiStatus').length, 1);
    await f.navigate('metadata');
    await f.navigate('prep');
    const request = f.get('optional-ai-request');
    assert.equal(request.disabled, false);
    request.value = 'Prepara una sesión house';
    request.dispatchEvent(new Event('input'));
    assert.equal(f.get('optional-ai-local-hold').hidden, false);
    assert.match(text(f.get('optional-ai-local-hold')), /operación local/i);
    assert.equal(f.get('optional-ai-prepare').disabled, true);
    assert.equal(f.calls.some(([kind]) => kind === 'aiPrepare'), false);
    assert.equal(f.calls.some(([kind]) => kind === 'aiRun'), false);
    finish(report); await settle();
    assert.equal(f.get('optional-ai-request').value, 'Prepara una sesión house');
    assert.equal(f.get('optional-ai-local-hold').hidden, true);
    assert.equal(f.get('optional-ai-prepare').disabled, false);
    f.click('optional-ai-prepare'); await settle();
    assert.equal(f.calls.filter(([kind]) => kind === 'aiPrepare').length, 1);
    assert.equal(f.calls.findLast(([kind]) => kind === 'aiPrepare')[1].surface, 'prep');
    assert.equal(f.calls.findLast(([kind]) => kind === 'aiPrepare')[1].request, 'Prepara una sesión house');
    assert.equal(f.calls.some(([kind]) => kind === 'aiRun'), false);
  } finally { f.restore(); }
});
test('AI draft is shared across surfaces and joins other dirty-close guards', async () => {
  const f = await fixture(); try { await f.openAi(); f.get('optional-ai-enabled').checked = false; f.get('optional-ai-enabled').dispatchEvent(new Event('change')); await f.navigate('preferences'); f.get('preferences-volume').value = '.4'; f.get('preferences-volume').dispatchEvent(new Event('input')); f.click('preferences-discard'); assert.equal(f.calls.filter(([kind])=>kind==='dirty').at(-1)[1], true); await f.navigate('ai'); assert.equal(f.get('optional-ai-enabled').checked, false); f.click('optional-ai-discard'); assert.equal(f.calls.filter(([kind])=>kind==='dirty').at(-1)[1], false); } finally { f.restore(); }
});
test('library Apply filters display only, has a clear action and retains the full engine library', async () => {
  const f = await fixture(); try { await aiResult(f); assert.equal(f.get('library-visible-count').textContent, '2 pistas'); f.click('optional-ai-apply'); await settle(); assert.equal(f.get('library-visible-count').textContent, '1 pista'); assert.equal(f.get('library-total').textContent, '2'); assert.match(f.get('ai-library-filter-notice').textContent, /IA/); await f.generate(); assert.equal(f.calls.findLast(([kind])=>kind==='generate')[1].targetTrackCount, 2); f.click('clear-ai-library-filter'); assert.equal(f.get('library-visible-count').textContent, '2 pistas'); } finally { f.restore(); }
});
test('Prep Apply only fills fields and local input changes revoke consent', async () => {
  const f = await fixture(); try { await aiResult(f,'prep'); f.click('optional-ai-apply'); await settle(); assert.equal(f.get('prep-name').value, 'Sesión propuesta'); assert.equal(f.get('prep-minutes').value, '30'); assert.equal(f.get('optional-ai-error').textContent, ''); assert.equal(f.calls.some(([kind])=>kind==='generate'), false); await aiReady(f,'prep'); f.get('prep-name').value='Cambio manual'; f.get('prep-name').dispatchEvent(new Event('input')); assert.equal(f.get('optional-ai-preview').hidden,true); assert.equal(f.get('optional-ai-consent').checked,false); } finally { f.restore(); }
});
test('editor improvement Apply stages a local preview from the exact ordered selector without touching the draft or the legacy request', async () => {
  const f = await fixture({ runAiRequest: async () => ({ cancelled: false, result: editorImprovementResult }), applyAiSuggestion: async () => ({ surface: 'editor', data: improvementPayload() }) });
  try {
    await openEditor(f);
    await aiReady(f, 'editor', 'Mejora el orden');
    assert.deepEqual(f.calls.findLast(([kind]) => kind === 'aiPrepare')[1], { surface: 'editor', request: 'Mejora el orden', context: { editId: aiUuid, draftIds: [tracks[0].id, tracks[1].id], includeReplacements: false } });
    f.click('optional-ai-ask'); await settle();
    f.click('optional-ai-apply'); await settle();
    assert.equal(f.get('optional-ai-error').textContent, '');
    assert.equal(f.get('editor-request').value, '');
    assert.equal(f.get('editor-dirty').textContent, 'Sin cambios pendientes');
    assert.equal(f.calls.some(([kind]) => kind === 'saveImprovement' || kind === 'saveEdit'), false);
  } finally { f.restore(); }
});
test('changing the draft order while a proposal is prepared invalidates it and reprepares with the exact current order', async () => {
  const f = await fixture();
  try {
    await openEditor(f);
    await aiReady(f, 'editor', 'Mejora el orden');
    assert.equal(f.get('optional-ai-consent').checked, true);
    f.click('editor-down-0'); await settle();
    assert.equal(f.get('optional-ai-preview').hidden, true);
    assert.equal(f.get('optional-ai-consent').checked, false);
    f.get('optional-ai-request').value = 'Mejora el orden'; f.get('optional-ai-request').dispatchEvent(new Event('input'));
    f.click('optional-ai-prepare'); await settle();
    assert.deepEqual(f.calls.findLast(([kind]) => kind === 'aiPrepare')[1].context, { editId: aiUuid, draftIds: [tracks[1].id, tracks[0].id], includeReplacements: false });
  } finally { f.restore(); }
});
test('renaming the draft while a proposal is prepared invalidates the disclosure identity', async () => {
  const f = await fixture();
  try {
    await openEditor(f);
    await aiReady(f, 'editor', 'Mejora el orden');
    assert.equal(f.get('optional-ai-consent').checked, true);
    f.get('editor-name').value = 'Otro nombre'; f.get('editor-name').dispatchEvent(new Event('input')); await settle();
    assert.equal(f.get('optional-ai-preview').hidden, true);
    assert.equal(f.get('optional-ai-consent').checked, false);
  } finally { f.restore(); }
});
test('a same-surface editor context refresh keeps the typed instruction ready to reprepare with a Spanish reminder', async () => {
  const f = await fixture();
  try {
    await openEditor(f);
    await aiReady(f, 'editor', 'Mejora el orden');
    f.get('editor-name').value = 'Otro nombre'; f.get('editor-name').dispatchEvent(new Event('input')); await settle();
    assert.equal(f.get('optional-ai-preview').hidden, true);
    assert.equal(f.get('optional-ai-consent').checked, false);
    assert.equal(f.get('optional-ai-request').value, 'Mejora el orden');
    assert.equal(f.get('optional-ai-prepare').disabled, false);
    assert.match(f.get('optional-ai-notice').textContent, /Contexto actualizado/);
    f.click('optional-ai-prepare'); await settle();
    assert.deepEqual(f.calls.findLast(([kind]) => kind === 'aiPrepare')[1], { surface: 'editor', request: 'Mejora el orden', context: { editId: aiUuid, draftIds: [tracks[0].id, tracks[1].id], includeReplacements: false } });
  } finally { f.restore(); }
});
test('a declined native confirmation keeps the prepared disclosure available for an explicit retry', async () => {
  let runs = 0; const f = await fixture({ runAiRequest: async () => { runs += 1; return { cancelled: true, result: null }; } });
  try {
    await aiReady(f, 'library', 'Busca house');
    assert.equal(f.get('optional-ai-preview').hidden, false);
    f.click('optional-ai-ask'); await settle();
    assert.equal(runs, 1);
    assert.equal(f.get('optional-ai-preview').hidden, false);
    assert.equal(f.get('optional-ai-consent').checked, false);
    assert.equal(f.get('optional-ai-result').hidden, true);
    assert.equal(f.get('optional-ai-notice').textContent, 'Envío cancelado: la vista previa sigue disponible; vuelve a marcar la autorización para reintentar.');
    f.get('optional-ai-consent').checked = true; f.get('optional-ai-consent').dispatchEvent(new Event('change'));
    f.click('optional-ai-ask'); await settle();
    assert.equal(runs, 2);
  } finally { f.restore(); }
});
test('an invalid improvement proposal shows the specific Spanish retry guidance in the panel', async () => {
  const f = await fixture({ runAiRequest: async () => { throw new Error('[invalid_improvement] private backend detail'); } });
  try {
    await openEditor(f);
    await aiReady(f, 'editor', 'Mejora el orden');
    f.click('optional-ai-ask'); await settle();
    assert.match(f.get('optional-ai-error').textContent, /playlist actual/);
    assert.doesNotMatch(f.get('optional-ai-error').textContent, /invalid_improvement|private backend/);
  } finally { f.restore(); }
});
test('changing the draft while a result is shown invalidates the result and any deferred apply', async () => {
  const f = await fixture({ runAiRequest: async () => ({ cancelled: false, result: editorImprovementResult }) });
  try {
    await openEditor(f);
    await aiReady(f, 'editor', 'Mejora el orden');
    f.click('optional-ai-ask'); await settle();
    assert.equal(f.get('optional-ai-result').hidden, false);
    f.click('editor-down-0'); await settle();
    assert.equal(f.get('optional-ai-result').hidden, true);
    assert.equal(f.get('optional-ai-apply').disabled, true);
  } finally { f.restore(); }
});
test('toggling replacements keeps the typed instruction while invalidating consent and resyncing the exact selector', async () => {
  const f = await fixture();
  try {
    await openEditor(f);
    await aiReady(f, 'editor', 'Mejora el orden');
    assert.equal(f.get('optional-ai-request').value, 'Mejora el orden');
    assert.equal(f.get('optional-ai-consent').checked, true);
    const toggle = f.get('optional-ai-include-replacements');
    assert.equal(toggle.hidden, false);
    toggle.checked = true; toggle.dispatchEvent(new Event('change')); await settle();
    assert.equal(toggle.checked, true);
    assert.equal(f.get('optional-ai-request').value, 'Mejora el orden');
    assert.equal(f.get('optional-ai-preview').hidden, true);
    assert.equal(f.get('optional-ai-consent').checked, false);
    f.click('optional-ai-prepare'); await settle();
    assert.equal(f.calls.findLast(([kind]) => kind === 'aiPrepare')[1].context.includeReplacements, true);
  } finally { f.restore(); }
});
test('the replacement toggle resyncs the improvement context, discards consent and never recurses', async () => {
  const f = await fixture();
  try {
    await openEditor(f);
    await aiReady(f, 'editor', 'Mejora el orden');
    assert.equal(f.get('optional-ai-consent').checked, true);
    const toggle = f.get('optional-ai-include-replacements');
    assert.equal(toggle.hidden, false);
    toggle.checked = true; toggle.dispatchEvent(new Event('change')); await settle();
    assert.equal(toggle.checked, true);
    assert.equal(f.get('optional-ai-preview').hidden, true);
    assert.equal(f.get('optional-ai-consent').checked, false);
    f.get('optional-ai-request').value = 'Mejora el orden'; f.get('optional-ai-request').dispatchEvent(new Event('input'));
    f.click('optional-ai-prepare'); await settle();
    assert.equal(f.calls.findLast(([kind]) => kind === 'aiPrepare')[1].context.includeReplacements, true);
  } finally { f.restore(); }
});
test('an editor draft outside the improvement bounds offers no AI surface instead of the legacy editId request', async () => {
  const many = Array.from({ length: 81 }, (_, index) => ({ ...tracks[0], id: index.toString(16).padStart(64, '0') }));
  const few = [{ ...tracks[0] }];
  for (const draftTracks of [many, few]) {
    const f = await fixture({ openPlaylistEditor: async () => ({ id: '1', editId: aiUuid, revision: 'r1', name: 'Set', tracks: draftTracks, missingTrackCount: 0 }) });
    try {
      await openEditor(f);
      assert.equal(f.get('ai-panel').hidden, true);
      assert.equal(f.calls.some(([kind]) => kind === 'aiPrepare'), false);
    } finally { f.restore(); }
  }
});
test('a bridge without the improvement save route disables the editor AI surface safely', async () => {
  const f = await fixture({ savePlaylistImprovement: undefined });
  try {
    await openEditor(f);
    assert.equal(f.get('ai-panel').hidden, true);
    assert.equal(f.calls.some(([kind]) => kind === 'aiPrepare'), false);
  } finally { f.restore(); }
});
test('a stale editor improvement payload is refused with an error and never changes or saves the draft', async () => {
  const f = await fixture({ runAiRequest: async () => ({ cancelled: false, result: editorImprovementResult }), applyAiSuggestion: async () => ({ surface: 'editor', data: improvementPayload({ sourceRevision: 'r9' }) }) });
  try {
    await openEditor(f);
    await aiReady(f, 'editor', 'Mejora el orden');
    f.click('optional-ai-ask'); await settle();
    f.click('optional-ai-apply'); await settle();
    assert.notEqual(f.get('optional-ai-error').textContent, '');
    assert.equal(f.get('editor-dirty').textContent, 'Sin cambios pendientes');
    assert.equal(f.calls.some(([kind]) => kind === 'saveImprovement' || kind === 'saveEdit'), false);
  } finally { f.restore(); }
});
test('a malformed editor improvement payload with a matching revision is refused at apply time without touching the draft', async () => {
  const malformed = improvementPayload({ assessment: { description: 'x', readiness: 'unknown', qualityScore: 1, warnings: [] } });
  const f = await fixture({ runAiRequest: async () => ({ cancelled: false, result: editorImprovementResult }), applyAiSuggestion: async () => ({ surface: 'editor', data: malformed }) });
  try {
    await openEditor(f);
    await aiReady(f, 'editor', 'Mejora el orden');
    f.click('optional-ai-ask'); await settle();
    f.click('optional-ai-apply'); await settle();
    assert.notEqual(f.get('optional-ai-error').textContent, '');
    assert.equal(f.get('editor-dirty').textContent, 'Sin cambios pendientes');
    assert.equal(f.calls.some(([kind]) => kind === 'saveImprovement' || kind === 'saveEdit'), false);
  } finally { f.restore(); }
});
test('saved Apply renders local selection and comparison as plain text without playlist mutation', async () => {
  const f = await fixture(); try { await aiResult(f,'playlists'); f.click('optional-ai-apply'); await settle(); assert.match(text(f.get('saved-ai-selection')),/Comparación local <img src=x>/); assert.equal(f.get('saved-ai-selection').hidden,false); assert.ok(!f.nodes().some(node=>node.tagName==='img')); assert.equal(f.calls.some(([kind])=>['save','rename','generate'].includes(kind)),false); } finally { f.restore(); }
});
test('AI cancellation prevents a late result and preserves the locally reviewed engine set', async () => {
  let finish; const f=await fixture({runAiRequest:()=>new Promise(resolve=>{finish=resolve;})}); try {await f.generate(); await aiReady(f,'review',''); f.click('optional-ai-ask'); assert.equal(f.get('cancel-operation').hidden,false); f.click('cancel-operation'); finish({cancelled:false,result:{resultId:aiUuid,surface:'review',kind:'commentary',title:'Late',text:'Late',proposal:null,canApply:false}}); await settle(); assert.equal(f.get('optional-ai-result').hidden,true); assert.equal(f.get('review-content').hidden,false); assert.match(f.get('operation-detail').textContent,/enviados.*recuperar/); } finally {f.restore();}
});
test('watch changes and core disconnect invalidate pending AI results and prior consent', async () => {
  let finish; const f=await fixture({runAiRequest:()=>new Promise(resolve=>{finish=resolve;})}); try {await aiReady(f); f.click('optional-ai-ask'); f.event(status({revision:2,changeState:'changed'})); f.offline(); finish({cancelled:false,result:{resultId:aiUuid,surface:'library',kind:'filters',title:'Late',text:'Late',proposal:{},canApply:true}}); await settle(); assert.equal(f.get('optional-ai-result').hidden,true); assert.equal(f.get('optional-ai-consent').checked,false); assert.equal(f.get('optional-ai-prepare').disabled,true); assert.equal(f.get('operation-label').textContent,'Servicio local desconectado');} finally {f.restore();}
});
test('opening saved AI during startup still completes local playlist bootstrap before applying suggestions', async () => {
  let finish;let reads=0;const f=await fixture({listLibrary:()=>new Promise(resolve=>{finish=resolve;}),listPlaylists:async()=>{reads++;return [{id:'1',name:'Set',trackCount:2,createdAt:''}];}});try{await f.navigate('playlists');await f.openAi();finish({tracks,count:2});await settle();assert.equal(reads,1);assert.match(text(f.get('playlists-list')),/Set/);assert.equal(f.calls.filter(([kind])=>kind==='aiStatus').length,1);}finally{f.restore();}
});
test('watch invalidation clears an applied AI display filter immediately without changing the engine library',async()=>{const f=await fixture();try{await aiResult(f);f.click('optional-ai-apply');await settle();assert.equal(f.get('library-visible-count').textContent,'1 pista');f.event(status({revision:2,changeState:'changed'}));assert.equal(f.get('library-visible-count').textContent,'2 pistas');assert.equal(f.get('ai-library-filter').hidden,true);assert.equal(f.get('library-total').textContent,'2');}finally{f.restore();}});
test('metadata and Live bind fixed explanations to their real local contexts', async()=>{
  const report={totalTracks:2,completeCount:2,incompleteCount:0,gaps:{bpm:0,camelot_key:0,energy_level:0},yearCoverage:{withReleaseYear:0,withoutReleaseYear:2},tracks:[],repairPlan:'Sin cambios',readOnly:true};
  const f=await fixture({getMetadataReport:async()=>report,getLiveStatus:async()=>({sessionId:aiUuid,revision:1,sourceReviewId:aiUuid,state:'active',current:tracks[0],history:[],candidates:[{track:tracks[1],score:1,alerts:[]}],elapsedSeconds:1})});try{await aiReady(f,'metadata','');assert.deepEqual(f.calls.findLast(([kind])=>kind==='aiPrepare')[1],{surface:'metadata',context:{},request:''});await f.generate();f.click('start-live');await settle();await aiReady(f,'live','');assert.deepEqual(f.calls.findLast(([kind])=>kind==='aiPrepare')[1],{surface:'live',context:{sessionId:aiUuid,revision:0},request:''});f.click('live-refresh');await settle();assert.equal(f.get('optional-ai-preview').hidden,true);assert.equal(f.get('optional-ai-consent').checked,false);}finally{f.restore();}
});
test('saved collections beyond200 require explicit bounded scope before exposing AI',async()=>{
  const items=Array.from({length:201},(_,n)=>({id:String(n+1),name:`Set ${n+1}`,trackCount:2,createdAt:''}));const f=await fixture({listPlaylists:async()=>items});try{await f.navigate('playlists');assert.equal(f.get('ai-panel').hidden,true);const choice=f.get('ai-saved-scope-1');choice.checked=true;choice.dispatchEvent(new Event('change'));assert.equal(f.get('ai-panel').hidden,false);await f.openAi();f.get('optional-ai-request').value='Compara';f.get('optional-ai-request').dispatchEvent(new Event('input'));f.click('optional-ai-prepare');await settle();assert.deepEqual(f.calls.findLast(([kind])=>kind==='aiPrepare')[1].context,{playlistIds:['1']});}finally{f.restore();}
});

for (const boundary of ['start','end','both']) test(`Prep AI Apply preserves selected ${boundary} boundaries`,async()=>{
 const proposal={targetTrackCount:2,name:'AI proposal',startTrackId:tracks[1].id,endTrackId:tracks[0].id};
 const f=await fixture({applyAiSuggestion:async()=>({surface:'prep',data:proposal})});
 try{await f.navigate('prep');if(boundary!=='end')f.get('prep-start').value=tracks[0].id;if(boundary!=='start')f.get('prep-end').value=tracks[1].id;
 // Do not introduce an overlapping unselected boundary in the single-boundary cases.
 if(boundary==='start')delete proposal.endTrackId;if(boundary==='end')delete proposal.startTrackId;
 await aiResult(f,'prep');f.click('optional-ai-apply');await settle();
 if(boundary!=='end')assert.equal(f.get('prep-start').value,tracks[0].id);if(boundary!=='start')assert.equal(f.get('prep-end').value,tracks[1].id);
 assert.equal(f.get('optional-ai-error').textContent,'');assert.equal(f.calls.some(([kind])=>kind==='generate'),false);
 }finally{f.restore();}
});

test('Prep AI Apply unions hard controls and never removes an exclusion to accept a conflicting boundary',async()=>{
 let proposal={targetTrackCount:2,name:'Reviewed proposal',requiredTrackIds:[],excludedTrackIds:[]};
 const f=await fixture({applyAiSuggestion:async()=>({surface:'prep',data:proposal})});
 try{await f.navigate('prep');const required=f.get('prep-required').options.find(option=>option.value===tracks[0].id);const excluded=f.get('prep-excluded').options.find(option=>option.value===tracks[1].id);required.selected=true;excluded.selected=true;
 await aiResult(f,'prep');f.click('optional-ai-apply');await settle();
 assert.equal(required.selected,true);assert.equal(excluded.selected,true);assert.equal(f.get('optional-ai-error').textContent,'');
 proposal={targetTrackCount:2,name:'Must not replace current name',startTrackId:tracks[1].id};
 await aiResult(f,'prep');const before=f.get('prep-name').value;f.click('optional-ai-apply');await settle();
 assert.equal(f.get('prep-start').value,'');assert.equal(f.get('prep-name').value,before);assert.equal(required.selected,true);assert.equal(excluded.selected,true);assert.notEqual(f.get('optional-ai-error').textContent,'');assert.equal(f.calls.some(([kind])=>kind==='generate'),false);
 }finally{f.restore();}
});

// --- I3 U4b: discoverable improvement CTA, readable before/after and honest apply/save ---
test('the editor summary CTA opens the existing AI panel, focuses the instruction and never prepares or contacts the provider', async () => {
  const f = await fixture();
  try {
    await openEditor(f);
    const cta = f.get('editor-improve');
    assert.equal(cta.disabled, false);
    f.click('editor-improve'); await settle();
    assert.equal(f.get('ai-panel').open, true);
    assert.equal(f.get('optional-ai-request').focused, true);
    assert.equal(f.calls.some(([kind]) => ['aiPrepare', 'aiRun', 'aiApply', 'saveEdit', 'saveImprovement'].includes(kind)), false);
  } finally { f.restore(); }
});
test('the editor CTA is disabled with an actionable hint outside the bounded draft and without the save bridge', async () => {
  const drafts = [[{ ...tracks[0] }], Array.from({ length: 81 }, (_, index) => ({ ...tracks[0], id: index.toString(16).padStart(64, '0') }))];
  for (const draftTracks of drafts) {
    const f = await fixture({ openPlaylistEditor: async () => ({ id: '1', editId: aiUuid, revision: 'r1', name: 'Set', tracks: draftTracks, missingTrackCount: 0 }) });
    try {
      await openEditor(f);
      assert.equal(f.get('editor-improve').disabled, true);
      assert.match(f.get('editor-improve-hint').textContent, /2 y 80/);
      assert.equal(f.calls.some(([kind]) => kind === 'aiPrepare'), false);
    } finally { f.restore(); }
  }
  const g = await fixture({ savePlaylistImprovement: undefined });
  try {
    await openEditor(g);
    assert.equal(g.get('editor-improve').disabled, true);
    assert.notEqual(g.get('editor-improve-hint').textContent, '');
    assert.equal(g.calls.some(([kind]) => kind === 'aiPrepare'), false);
  } finally { g.restore(); }
});
test('reviewing an improvement result stages a read-only before/after preview and never touches draft or save', async () => {
  const f = await fixture({ runAiRequest: async () => ({ cancelled: false, result: editorImprovementResult }), applyAiSuggestion: async () => ({ surface: 'editor', data: improvementPayload() }) });
  try {
    await openEditor(f);
    await aiReady(f, 'editor', 'Mejora el orden');
    f.click('optional-ai-ask'); await settle();
    assert.equal(f.get('optional-ai-apply').textContent, 'Revisar propuesta local');
    f.click('optional-ai-apply'); await settle();
    assert.equal(f.get('optional-ai-error').textContent, '');
    assert.equal(f.get('editor-improvement').hidden, false);
    assert.match(text(f.get('editor-improvement')), /antes/i);
    assert.match(text(f.get('editor-improvement')), /después/i);
    assert.equal(f.get('editor-improvement-apply').disabled, false);
    assert.equal(f.get('editor-dirty').textContent, 'Sin cambios pendientes');
    assert.equal(f.calls.some(([kind]) => kind === 'saveImprovement' || kind === 'saveEdit'), false);
    assert.doesNotMatch(f.get('optional-ai-notice').textContent, /aplicad[ao] al trabajo local/i);
    assert.match(f.get('optional-ai-notice').textContent, /borrador/i);
  } finally { f.restore(); }
});
test('applying the improvement changes only the draft, labels the bound save and persists through the dedicated command', async () => {
  const f = await fixture({ runAiRequest: async () => ({ cancelled: false, result: editorImprovementResult }), applyAiSuggestion: async () => ({ surface: 'editor', data: improvementPayload() }) });
  try {
    await openEditor(f);
    await aiReady(f, 'editor', 'Mejora el orden');
    f.click('optional-ai-ask'); await settle();
    f.click('optional-ai-apply'); await settle();
    assert.equal(f.get('editor-improvement-counts').textContent, '0 pistas añadidas · 0 pistas quitadas · 2 movidas');
    assert.deepEqual(f.get('editor-improvement-after').children.map((node) => node.textContent), ['1. b · DJ · #2 → #1', '2. a · DJ · #1 → #2']);
    f.click('editor-improvement-apply'); await settle();
    assert.equal(f.get('editor-save').textContent, 'Guardar mejora');
    assert.equal(f.get('editor-dirty').textContent, 'Cambios sin guardar');
    assert.equal(f.get('operation-label').textContent, 'Mejora aplicada al borrador. Usa «Guardar mejora» para conservarla en la playlist.');
    assert.equal(f.get('operation-detail').textContent, '');
    assert.doesNotMatch(f.get('operation-detail').textContent, /no cambió y no se guardó/);
    assert.equal(f.calls.some(([kind]) => kind === 'saveImprovement'), false);
    f.click('editor-save'); await settle();
    const saved = f.calls.findLast(([kind]) => kind === 'saveImprovement');
    assert.ok(saved); assert.equal(saved[1].proposalId, 'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee');
    assert.equal(f.calls.some(([kind]) => kind === 'saveEdit'), false);
    assert.equal(f.get('operation-label').textContent, 'Mejora guardada en la playlist. Ya no hay cambios pendientes.');
    assert.equal(f.get('operation-detail').textContent, '');
    assert.equal(f.get('editor-save').textContent, 'Guardar cambios');
  } finally { f.restore(); }
});
test('the ordinary editor save keeps its own confirmation copy after the improvement binding is revoked', async () => {
  const f = await fixture({ runAiRequest: async () => ({ cancelled: false, result: editorImprovementResult }), applyAiSuggestion: async () => ({ surface: 'editor', data: improvementPayload() }) });
  try {
    await openEditor(f);
    await aiReady(f, 'editor', 'Mejora el orden');
    f.click('optional-ai-ask'); await settle();
    f.click('optional-ai-apply'); await settle();
    f.click('editor-improvement-apply'); await settle();
    f.get('editor-name').value = 'Otro nombre'; f.get('editor-name').dispatchEvent(new Event('input')); await settle();
    f.click('editor-save'); await settle();
    assert.ok(f.calls.some(([kind]) => kind === 'saveEdit'));
    assert.equal(f.calls.some(([kind]) => kind === 'saveImprovement'), false);
    assert.equal(f.get('operation-label').textContent, 'Cambios guardados');
    assert.equal(f.get('operation-detail').textContent, 'Los cambios solo se conservan al pulsar Guardar cambios');
  } finally { f.restore(); }
});
test('a manual change after applying revokes the binding and restores the manual save command', async () => {
  const f = await fixture({ runAiRequest: async () => ({ cancelled: false, result: editorImprovementResult }), applyAiSuggestion: async () => ({ surface: 'editor', data: improvementPayload() }) });
  try {
    await openEditor(f);
    await aiReady(f, 'editor', 'Mejora el orden');
    f.click('optional-ai-ask'); await settle();
    f.click('optional-ai-apply'); await settle();
    f.click('editor-improvement-apply'); await settle();
    assert.equal(f.get('editor-save').textContent, 'Guardar mejora');
    f.get('editor-name').value = 'Otro nombre'; f.get('editor-name').dispatchEvent(new Event('input')); await settle();
    assert.equal(f.get('editor-save').textContent, 'Guardar cambios');
    f.click('editor-save'); await settle();
    assert.equal(f.calls.some(([kind]) => kind === 'saveImprovement'), false);
    assert.ok(f.calls.some(([kind]) => kind === 'saveEdit'));
  } finally { f.restore(); }
});
test('other AI surfaces keep their original review and apply copy', async () => {
  const f = await fixture();
  try {
    await aiResult(f);
    assert.equal(f.get('optional-ai-apply').textContent, 'Aplicar propuesta al trabajo local');
    f.click('optional-ai-apply'); await settle();
    assert.match(f.get('operation-detail').textContent, /aplicada al trabajo local/i);
  } finally { f.restore(); }
});

// --- F10: the editor CTA must explain AI settings that block every panel action ---
test('the editor loads local AI settings so the CTA can refuse before the AI panel is opened', async () => {
  const f = await fixture({ getAiStatus: async () => ({ ...aiStatus, enabled: false }) });
  try {
    await openEditor(f);
    assert.equal(f.get('editor-improve').disabled, true);
    assert.match(f.get('editor-improve-hint').textContent, /Ajustes/);
    assert.equal(f.calls.some(([kind]) => kind === 'aiPrepare'), false);
  } finally { f.restore(); }
});
test('the editor CTA is disabled with a settings hint when AI is off or unconfigured', async () => {
  for (const patch of [{ enabled: false }, { configured: false, credentialLabel: null }]) {
    const f = await fixture({ getAiStatus: async () => ({ ...aiStatus, ...patch }) });
    try {
      await f.openAi();
      await openEditor(f);
      assert.equal(f.get('editor-improve').disabled, true);
      assert.match(f.get('editor-improve-hint').textContent, /Ajustes/);
      assert.equal(f.calls.some(([kind]) => kind === 'aiPrepare'), false);
    } finally { f.restore(); }
  }
});
test('the editor CTA re-renders with a save-or-discard hint when the AI draft becomes dirty', async () => {
  const f = await fixture({ getAiStatus: async () => ({ ...aiStatus, enabled: false }) });
  try {
    await openEditor(f);
    assert.equal(f.get('editor-improve').disabled, true);
    f.get('optional-ai-enabled').checked = true;
    f.get('optional-ai-enabled').dispatchEvent(new Event('change'));
    await settle();
    assert.equal(f.get('editor-improve').disabled, true);
    assert.match(f.get('editor-improve-hint').textContent, /cambios de IA/);
  } finally { f.restore(); }
});

test('the review screen offers the bot button, and the floating «Asistente de lista» keeps the whole chat with history on open, a turn, a reset and the untouched review commentary', async () => {
  const f = await fixture();
  try {
    await f.generate();
    assert.equal(f.get('bot-window-root').hidden, false);
    assert.equal(f.get('bot-window').hidden, true);
    assert.equal(f.get('bot-window-toggle').attrs['aria-label'], 'Abrir asistente de lista');
    assert.ok(!all(f.get('ai-panel')).some((node) => node.id === 'list-chat-container'), 'the list chat left the AI panel');
    assert.equal(f.calls.some(([kind]) => kind === 'aiChatHistory'), false);
    // Opening the existing AI panel no longer loads the list conversation.
    await f.openAi();
    assert.equal(f.calls.some(([kind]) => kind === 'aiChatHistory'), false);
    f.click('bot-window-toggle'); await settle();
    assert.equal(f.get('bot-window').hidden, false);
    assert.equal(f.get('bot-window-heading').textContent, 'Asistente de lista');
    assert.equal(f.calls.filter(([kind]) => kind === 'aiChatHistory').length, 1);
    assert.match(text(f.get('list-chat-empty')), /Pregunta cómo mejorar esta lista/);
    const draft = f.get('list-chat-request');
    draft.value = '¿Qué transiciones son las más débiles?';
    draft.dispatchEvent(new Event('input'));
    f.click('list-chat-send'); await settle();
    assert.deepEqual(f.calls.findLast(([kind]) => kind === 'aiPrepare')[1], { surface: 'chat', request: '¿Qué transiciones son las más débiles?', context: { reviewId: aiUuid } });
    assert.deepEqual(f.calls.findLast(([kind]) => kind === 'aiRun')[1], { previewId: aiUuid });
    assert.match(text(f.get('list-chat-conversation')), /Pista sugerida: la segunda\./);
    assert.equal(f.get('list-chat-request').value, '');
    assert.equal(f.get('list-chat-pending').hidden, true);
    // Minimizar hides the window and keeps the conversation; the button reopens it.
    f.click('bot-window-minimize'); await settle();
    assert.equal(f.get('bot-window').hidden, true);
    assert.match(text(f.get('list-chat-conversation')), /Pista sugerida: la segunda\./);
    f.click('bot-window-toggle'); await settle();
    assert.equal(f.get('bot-window').hidden, false);
    f.click('list-chat-reset'); await settle();
    assert.equal(f.calls.some(([kind]) => kind === 'aiChatReset'), true);
    assert.equal(f.get('list-chat-conversation').children.length, 0);
    assert.equal(f.get('list-chat-empty').hidden, false);
    // The existing review commentary keeps working beside the chat.
    f.click('optional-ai-prepare'); await settle();
    assert.deepEqual(f.calls.findLast(([kind]) => kind === 'aiPrepare')[1], { surface: 'review', request: '', context: { reviewId: aiUuid } });
    await f.navigate('library');
    assert.equal(f.get('bot-window-root').hidden, true);
    assert.equal(f.get('bot-window').hidden, true);
  } finally { f.restore(); }
});
test('the bot badge counts the proposed changes and clears once they are applied, and Escape minimizes the window', async () => {
  const f = await fixture({ aiChatApply: async (input) => { f.calls.push(['aiChatApply', input]); return { review: appliedChatReview, actions: [] }; } });
  try {
    await f.generate();
    f.chatActions([chatMove]);
    assert.equal(f.get('bot-window-badge').hidden, true, 'nothing pending before the window reads the conversation');
    f.click('bot-window-toggle'); await settle();
    assert.equal(f.get('bot-window-badge').hidden, false);
    assert.equal(f.get('bot-window-badge').textContent, '1');
    f.click('list-chat-apply-0'); await settle();
    assert.equal(f.get('bot-window-badge').hidden, true);
    assert.equal(f.get('bot-window').hidden, false);
    window.dispatchEvent(Object.assign(new Event('keydown'), { key: 'Escape' }));
    await settle();
    assert.equal(f.get('bot-window').hidden, true);
    assert.equal(f.get('list-chat-empty').hidden, false, 'the chat stays mounted while minimised');
  } finally { f.restore(); }
});
const chatMove = { actionId: '33333333-3333-4333-8333-333333333333', type: 'move', position: 1, to: 2, title: 'a', artist: 'DJ', reason: 'Sube la energía del inicio' };
const appliedChatReview = { reviewId: '22222222-2222-4222-8222-222222222222', tracks: [{ ...tracks[0], title: 'Cambio aplicado' }, tracks[1]], warnings: [], blockers: [], name: 'Set', variant: 'balanced', readiness: 'ready' };
test('the review assistant shows the pending actions from history and one click applies a change on screen', async () => {
  const f = await fixture({ aiChatApply: async (input) => { f.calls.push(['aiChatApply', input]); return { review: appliedChatReview, actions: [] }; } });
  try {
    await f.generate();
    f.chatActions([chatMove]);
    f.click('bot-window-toggle'); await settle();
    // S9 is off for this turn: the cards stay and one click applies one change.
    f.get('list-chat-auto-toggle').checked = false;
    f.get('list-chat-auto-toggle').dispatchEvent(new Event('change'));
    assert.equal(f.get('list-chat-proposed').hidden, false);
    assert.match(text(f.get('list-chat-proposed')), /Cambios propuestos/);
    assert.equal(f.get('list-chat-proposed-actions').children[0].children[0].textContent, 'Mover 1. a a la posición 2');
    const draft = f.get('list-chat-request');
    draft.value = '¿Qué pistas cambio?';
    draft.dispatchEvent(new Event('input'));
    f.click('list-chat-send'); await settle();
    assert.ok(text(f.get('list-chat-conversation')).includes('Pista sugerida: la segunda.'));
    f.click('list-chat-apply-0'); await settle();
    assert.deepEqual(f.calls.findLast(([kind]) => kind === 'aiChatApply')[1], { actionId: chatMove.actionId });
    assert.ok(text(f.get('review-table')).includes('Cambio aplicado'));
    assert.equal(f.get('list-chat-notice').textContent, 'Cambio aplicado. Puedes deshacerlo con Deshacer.');
    assert.equal(f.get('list-chat-proposed').hidden, true);
    // The edit minted a new review, but this conversation and its cards keep their place.
    assert.ok(text(f.get('list-chat-conversation')).includes('Pista sugerida: la segunda.'));
    assert.equal(f.get('list-chat-pending').hidden, true);
  } finally { f.restore(); }
});
test('a stale assistant action shows the existing Spanish error and removes the cards', async () => {
  const f = await fixture({ aiChatApply: async () => { throw Object.assign(new Error('gone'), { code: 'stale_ai' }); } });
  try {
    await f.generate();
    f.chatActions([chatMove]);
    f.click('bot-window-toggle'); await settle();
    assert.equal(f.get('list-chat-proposed').hidden, false);
    f.click('list-chat-apply-0'); await settle();
    assert.equal(f.get('list-chat-error').hidden, false);
    assert.equal(f.get('list-chat-error').textContent, 'El contexto o la solicitud cambió. Prepara otra vista previa y revisa de nuevo el consentimiento.');
    assert.equal(f.get('list-chat-proposed').hidden, true);
    assert.ok(!text(f.get('review-table')).includes('Cambio aplicado'));
  } finally { f.restore(); }
});
const chatExtend = { actionId: '44444444-4444-4444-8444-444444444444', type: 'extend', to: 20, reason: 'Faltaron pistas para la sesión' };
const chatVariant = { actionId: '55555555-5555-4555-8555-555555555555', type: 'use_variant', variant: 'adventurous', trackCount: 20, reason: 'La exploratoria entra sin perder el orden' };
const chatPlan = () => [['safe', 4], ['balanced', 4], ['adventurous', 20]].map(([name, trackCount]) => ({ name, description: `Motor ${name}`, trackCount, warnings: [], blockers: [], readiness: 'ready', qualityScore: .8 }));
test('the assistant extend card grows the list and shows the added count', async () => {
  const f = await fixture({ aiChatApply: async (input) => { f.calls.push(['aiChatApply', input]); return { review: appliedChatReview, actions: [], extended: { requested: 18, added: 18, outsideGenre: 0 } }; } });
  try {
    await f.generate();
    f.chatActions([chatExtend]);
    f.click('bot-window-toggle'); await settle();
    assert.equal(f.get('list-chat-proposed-actions').children[0].children[0].textContent, 'Ampliar la lista a 20 pistas');
    f.click('list-chat-apply-0'); await settle();
    assert.deepEqual(f.calls.findLast(([kind]) => kind === 'aiChatApply')[1], { actionId: chatExtend.actionId });
    assert.ok(text(f.get('review-table')).includes('Cambio aplicado'));
    assert.equal(f.get('list-chat-notice').textContent, 'Se agregaron 18 pistas.');
  } finally { f.restore(); }
});
test('choosing the proposed alternative opens that variant and starts a new conversation', async () => {
  const f = await fixture({
    generatePrep: async (input) => { f.calls.push(['generate', input]); return { reviewId: aiUuid, planId: 'plan', variants: chatPlan(), name: 'Set', variant: 'balanced', readiness: 'ready', tracks, warnings: [], blockers: [] }; },
    selectPrepVariant: async (input) => { f.calls.push(['select', input]); return { reviewId: '66666666-6666-4666-8666-666666666666', name: 'Set', variant: input.variant, readiness: 'ready', tracks: [...tracks, tracks[0]], warnings: [], blockers: [] }; },
  });
  try {
    await f.generate();
    f.chatActions([chatVariant]);
    f.click('bot-window-toggle'); await settle();
    assert.equal(f.get('list-chat-proposed-actions').children[0].children[0].textContent, 'Usar la alternativa exploratoria (20 pistas)');
    f.click('list-chat-apply-0'); await settle();
    assert.deepEqual(f.calls.find(([kind]) => kind === 'select')[1], { planId: 'plan', variant: 'adventurous' });
    assert.equal(f.get('review-variant').textContent, 'SELECCIÓN AVENTURERA');
    assert.equal(f.get('list-chat-notice').textContent, 'Se cambió la alternativa. La conversación empieza de nuevo.');
    assert.equal(f.get('list-chat-conversation').children.length, 0);
  } finally { f.restore(); }
});
// --- S9: automatic apply with one batch undo ---
const chatRemove = { actionId: '77777777-7777-4777-8777-777777777777', type: 'remove', position: 1, title: 'a', artist: 'DJ', reason: 'Choca de tonalidad con la segunda' };
const chatReorder = { actionId: '88888888-8888-4888-8888-888888888888', type: 'reorder', moved: 2, reason: 'La curva de energía sube antes' };
const manualReview = { ...appliedChatReview, reviewId: '99999999-9999-4999-8999-999999999999' };
test('the review assistant applies a whole reply at once with the switch on and one manual edit retires the batch undo', async () => {
  const applied = [];
  const f = await fixture({
    reviewDetails: async () => ({ ...appliedChatReview, transitions: [], readinessChecks: [], readinessSummary: '', engineFacts: '' }),
    reviewCompare: async () => ({ reviewId: aiUuid, available: false, replacement: null, original: {}, proposed: {}, message: '' }),
    reviewRemove: async (input) => { f.calls.push(['reviewRemove', input]); return manualReview; },
    reviewReorder: async (input) => { f.calls.push(['reviewReorder', input]); return manualReview; },
    reviewUndo: async (input) => { f.calls.push(['reviewUndo', input]); return manualReview; },
    aiChatApply: async (input) => { applied.push(input.actionId); return { review: appliedChatReview, actions: input.actionId === chatRemove.actionId ? [chatReorder] : [] }; },
  });
  try {
    await f.generate();
    f.chatActions([chatRemove, chatReorder]);
    f.click('bot-window-toggle'); await settle();
    assert.equal(f.get('list-chat-auto-toggle').checked, true, 'the switch is on by default');
    const draft = f.get('list-chat-request');
    draft.value = 'Quita la primera y reordena'; draft.dispatchEvent(new Event('input'));
    f.click('list-chat-send'); await settle();
    assert.deepEqual(applied, [chatRemove.actionId, chatReorder.actionId], 'the whole reply is applied in order');
    assert.equal(f.get('list-chat-auto-applied').hidden, false);
    assert.equal(f.get('list-chat-auto-notice').textContent, 'Se aplicaron 2 cambios.');
    assert.deepEqual(f.get('list-chat-auto-list').children.map((node) => node.textContent), ['Quitar 1. a', 'Reordenar la lista (2 pistas cambian de lugar)']);
    assert.equal(f.get('list-chat-undo-batch').textContent, 'Deshacer estos cambios');
    assert.equal(f.get('list-chat-undo-batch').hidden, false);
    assert.equal(f.get('list-chat-proposed').hidden, true, 'no card was left to approve');
    assert.ok(text(f.get('review-table')).includes('Cambio aplicado'));
    // A manual edit of the same list retires the batch undo.
    f.click('review-remove-0'); await settle();
    assert.ok(f.calls.some(([kind]) => kind === 'reviewRemove'));
    assert.equal(f.get('list-chat-undo-batch').hidden, true);
    assert.equal(f.get('list-chat-auto-applied').hidden, true);
  } finally { f.restore(); }
});
