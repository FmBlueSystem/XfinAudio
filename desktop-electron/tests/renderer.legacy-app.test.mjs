import assert from 'node:assert/strict';
import test from 'node:test';
class Element extends EventTarget {
  constructor(tag = 'div') { super(); this.tagName = tag; }
  textContent = ''; value = ''; checked = false; disabled = false; hidden = false; dataset = {}; children = []; attrs = {}; classes = new Set(); paused = true; duration = 0; currentTime = 0;
  classList = { toggle: (key, active) => active ? this.classes.add(key) : this.classes.delete(key), contains: (key) => this.classes.has(key) };
  setAttribute(key, value) { this.attrs[key] = value; } removeAttribute(key) { delete this.attrs[key]; }
  append(...nodes) { this.children.push(...nodes); } replaceChildren(...nodes) { this.children = nodes; } closest() { return null; } focus() {} pause() { this.paused = true; } load() {} async play() { this.paused = false; }
}
const all = (node) => [node, ...node.children.flatMap(all)]; const text = (node) => [node.textContent, ...node.children.map(text)].join(' ');
const tick = () => new Promise((resolve) => setImmediate(resolve)); const settle = async () => { for (let i = 0; i < 5; i++) await tick(); };
const prefs = (patch = {}) => ({ revision: 'a'.repeat(64), previewVolume: .25, watchLibrary: true, recoveryWarning: false, libraryLabels: ['DJ'], capabilities: { loudnessWriteback: false, providers: false, language: 'es' }, ...patch });
const status = (patch = {}) => ({ revision: 1, changeState: 'restored', watchState: 'active', rootCount: 1, watchedCount: 1, ...patch });
const tracks = ['a', 'b'].map((id) => ({ id: id.repeat(64), title: id, artist: 'DJ', bpm: 120, key: '8A', energy: 5, duration: 120, missing: false }));
let sequence = 0;
async function fixture(overrides = {}) {
  const previousDocument = globalThis.document; const previousWindow = globalThis.window; const elements = new Map(); const calls = []; let onStatus; let progress; let statusUnsubscribed = false;
  const nodes = () => [...elements.values()].flatMap(all); const get = (id) => { const dynamic = nodes().find((node) => node.id === id); if (dynamic) return dynamic; if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  const routes = ['library', 'preferences', 'playlists', 'editor', 'review', 'live', 'serato'].map((route) => { const button = new Element('button'); button.dataset.route = route; return button; });
  const api = {
    listLibrary: async () => { calls.push(['library']); return { tracks, count: 2 }; }, getPrepCatalog: async () => ({ strategies: [] }), onProgress: (callback) => { progress = callback; return () => {}; },
    getPreferences: async () => { calls.push(['preferences']); return prefs(); }, savePreferences: async (input) => { calls.push(['savePreferences', input]); return prefs({ ...input, revision: 'b'.repeat(64) }); },
    getLibraryStatus: async () => { calls.push(['status']); return status(); }, onLibraryStatus: (callback) => { onStatus = callback; return () => { statusUnsubscribed = true; }; },
    rescanLibrary: async () => { calls.push(['rescan']); return { tracks, count: 2 }; }, setDraftDirty: async (dirty) => { calls.push(['dirty', dirty]); },
    listPlaylists: async () => [{ id: '1', name: 'Set', trackCount: 2, createdAt: '' }], openPlaylistEditor: async () => ({ id: '1', editId: 'edit', revision: 'r1', name: 'Set', tracks, missingTrackCount: 0 }), discardPlaylistEdit: async () => ({ id: '1', editId: 'edit', revision: 'r1', name: 'Set', tracks, missingTrackCount: 0 }),
    generatePrep: async () => ({ reviewId: 'review', name: 'Set', variant: 'balanced', readiness: 'ready', tracks, warnings: [], blockers: [] }),
    openLive: async () => ({ sessionId: 'live', revision: 0, sourceReviewId: 'review', state: 'active', current: tracks[0], history: [], candidates: [{ track: tracks[1], score: 1, alerts: [] }], elapsedSeconds: 0 }),
    chooseSeratoDestination: async () => ({ destinationId: 'dest', label: '_Serato_' }), previewSeratoExport: async () => ({ previewId: 'preview', sourceRevision: 'r', filename: 'Set.crate', destinationLabel: '_Serato_', trackCount: 2, readiness: 'ready', warnings: [], blockers: [], canCommit: true, tracks, backup: { required: false } }), ...overrides,
  };
  globalThis.document = { getElementById: get, createElement: (tag) => new Element(tag), title: '', querySelectorAll: (selector) => selector === '[data-route]' || selector === '.nav-item' ? routes : selector === '[data-mutation]' ? nodes().filter((node) => 'mutation' in node.dataset) : [] };
  globalThis.window = Object.assign(new EventTarget(), { xfin: api }); for(const id of ['choose-library','choose-library-empty','refresh-playlists','refresh-metadata'])get(id).dataset.mutation='';get('metadata-filter').value = 'all'; get('prep-count').value = '2';
  await import(`../.out/renderer/app.js?legacyApp=${++sequence}`); await settle();
  const click = (id) => get(id).dispatchEvent(new Event('click')); const navigate = async (route) => { routes.find((button) => button.dataset.route === route).dispatchEvent(new Event('click')); await settle(); };
  return { get, calls, nodes, click, navigate, event: (value) => { assert.equal(typeof onStatus, 'function'); onStatus(value); }, offline: () => progress({ operation: 'core', phase: 'error', message: '/private/core' }), statusUnsubscribed: () => statusUnsubscribed, generate: async () => { get('prep-form').dispatchEvent(new Event('submit', { cancelable: true })); await settle(); }, restore: () => { window.dispatchEvent(new Event('beforeunload')); globalThis.document = previousDocument; globalThis.window = previousWindow; } };
}
const legacyPreview={previewId:'a'.repeat(32),mode:'fresh-profile-only',trackCount:2,cachedTrackCount:2,playlistCount:1,referenceCount:2,playlistNames:['Original set'],safePreferences:{previewVolume:.4,spectralCohesion:.8},requiresRootAuthorization:true,sourceUnchanged:true};
const legacyResult={imported:true,restartRequired:true,backupRetained:true,requiresRootAuthorization:true,trackCount:2,playlistCount:1};
const legacyApi=(calls)=>({previewLegacyImport:async()=>{calls.push(['preview']);return legacyPreview;},applyLegacyImport:async params=>{calls.push(['apply',params]);return legacyResult;},discardLegacyImport:async params=>{calls.push(['discard',params]);return {discarded:true};}});
test('legacy import only starts explicitly and respects dirty drafts before native preview',async()=>{
 const calls=[];const f=await fixture(legacyApi(calls));try{assert.deepEqual(calls,[]);await f.navigate('preferences');assert.equal(f.get('legacy-import-choose').tagName,'button');f.get('preferences-volume').value='.4';f.get('preferences-volume').dispatchEvent(new Event('input'));assert.equal(f.get('legacy-import-choose').disabled,true);f.click('legacy-import-choose');assert.deepEqual(calls,[]);f.click('preferences-discard');f.click('legacy-import-choose');await settle();assert.deepEqual(calls,[['preview']]);assert.match(f.get('legacy-import-summary').textContent,/2 pistas/);f.click('legacy-import-discard');await settle();assert.deepEqual(calls.at(-1),['discard',{previewId:'a'.repeat(32)}]);assert.equal(f.get('legacy-import-apply').disabled,true);}finally{f.restore();}
});
test('confirmed import drains without cancel, clears playback, freezes every route and preserves visible restart receipt',async()=>{
 const calls=[];let finish;const f=await fixture({...legacyApi(calls),applyLegacyImport:params=>{calls.push(['apply',params]);return new Promise(resolve=>finish=resolve);}});try{
  const play=f.nodes().find(node=>node.dataset.trackId===tracks[0].id);play.dispatchEvent(new Event('click'));await settle();assert.equal(f.get('audio-player').paused,false);await f.navigate('preferences');f.click('legacy-import-choose');await settle();f.click('legacy-import-apply');assert.equal(f.get('audio-player').paused,true);assert.equal(f.get('cancel-operation').hidden,true);assert.equal(f.get('legacy-import-choose').disabled,true);finish(legacyResult);await settle();assert.match(f.get('legacy-import-summary').textContent,/Importación completada/);assert.match(f.get('operation-label').textContent,/Reinicio necesario/);assert.equal(f.get('choose-library').disabled,true);assert.equal(f.get('generate-prep').disabled,true);assert.equal(f.get('player-toggle').disabled,true);
  await f.navigate('library');play.dispatchEvent(new Event('click'));assert.equal(f.get('audio-player').paused,true);await f.navigate('preferences');assert.match(f.get('legacy-import-summary').textContent,/Importación completada/);assert.equal(f.get('legacy-import-choose').disabled,true);assert.equal(calls.filter(([kind])=>kind==='apply').length,1);
 }finally{f.restore();}
});
test('required restart from a renderer reload or uncertain receipt blocks further work with safe guidance',async()=>{
 const reload=await fixture({...legacyApi([]),listLibrary:async()=>{throw Error('[legacy_restart_required] /private/profile');}});try{assert.match(reload.get('operation-label').textContent,/Reinicio necesario/);assert.equal(reload.get('choose-library').disabled,true);assert.doesNotMatch(reload.get('operation-detail').textContent,/private/);}finally{reload.restore();}
 const uncertain=await fixture({...legacyApi([]),applyLegacyImport:async()=>{throw Error('[legacy_recovery_required] /private/profile');}});try{await uncertain.navigate('preferences');uncertain.click('legacy-import-choose');await settle();uncertain.click('legacy-import-apply');await settle();assert.match(uncertain.get('operation-label').textContent,/Reinicio necesario/);assert.equal(uncertain.get('generate-prep').disabled,true);assert.doesNotMatch(uncertain.get('legacy-import-error').textContent,/private/);}finally{uncertain.restore();}
});
