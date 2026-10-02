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
const profileStatus = (patch = {}) => ({state:'partial',totalTracks:2,readyCount:0,spectralReadyCount:0,danceabilityReadyCount:0,edgeReadyCount:0,pendingCount:2,failedCount:0,...patch});
const completion = (patch = {}) => ({cancelled:false,tracks,status:profileStatus({state:'complete',readyCount:2,spectralReadyCount:2,danceabilityReadyCount:2,edgeReadyCount:2,pendingCount:0}),completeCount:2,incompleteCount:0,...patch});
let sequence = 0;
async function fixture(overrides = {}) {
  const previousDocument = globalThis.document; const previousWindow = globalThis.window; const elements = new Map(); const calls = []; let onStatus; let progress; let statusUnsubscribed = false;
  const nodes = () => [...elements.values()].flatMap(all); const get = (id) => { const dynamic = nodes().find((node) => node.id === id); if (dynamic) return dynamic; if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  const routes = ['library', 'preferences', 'playlists', 'editor', 'review', 'live', 'serato'].map((route) => { const button = new Element('button'); button.dataset.route = route; return button; });
  const api = {
    listLibrary: async () => { calls.push(['library']); return { tracks, count: 2 }; }, getPrepCatalog: async () => ({ strategies: [] }), onProgress: (callback) => { progress = callback; return () => {}; },
    getPreferences: async () => { calls.push(['preferences']); return prefs(); }, savePreferences: async (input) => { calls.push(['savePreferences', input]); return prefs({ ...input, revision: 'b'.repeat(64) }); },
    getLibraryStatus: async () => { calls.push(['status']); return status(); }, onLibraryStatus: (callback) => { onStatus = callback; return () => { statusUnsubscribed = true; }; },
    getProfileStatus: async () => { calls.push(['profileStatus']); return profileStatus(); }, getProfileSettings: async () => { calls.push(['profileSettings']); return {revision:'a'.repeat(64),spectralCohesion:.5}; }, saveProfileSettings: async (input) => {calls.push(['saveProfileSettings',input]);return {...input,revision:'b'.repeat(64)};}, completeProfiles: async () => {calls.push(['completeProfiles']);return completion();},
    rescanLibrary: async () => { calls.push(['rescan']); return { tracks, count: 2 }; }, setDraftDirty: async (dirty) => { calls.push(['dirty', dirty]); },
    listPlaylists: async () => [{ id: '1', name: 'Set', trackCount: 2, createdAt: '' }], openPlaylistEditor: async () => ({ id: '1', editId: 'edit', revision: 'r1', name: 'Set', tracks, missingTrackCount: 0 }), discardPlaylistEdit: async () => ({ id: '1', editId: 'edit', revision: 'r1', name: 'Set', tracks, missingTrackCount: 0 }),
    generatePrep: async () => ({ reviewId: 'review', name: 'Set', variant: 'balanced', readiness: 'ready', tracks, warnings: [], blockers: [] }),
    openLive: async () => ({ sessionId: 'live', revision: 0, sourceReviewId: 'review', state: 'active', current: tracks[0], history: [], candidates: [{ track: tracks[1], score: 1, alerts: [] }], elapsedSeconds: 0 }),
    chooseSeratoDestination: async () => ({ destinationId: 'dest', label: '_Serato_' }), previewSeratoExport: async () => ({ previewId: 'preview', sourceRevision: 'r', filename: 'Set.crate', destinationLabel: '_Serato_', trackCount: 2, readiness: 'ready', warnings: [], blockers: [], canCommit: true, tracks, backup: { required: false } }), ...overrides,
  };
  globalThis.document = { getElementById: get, createElement: (tag) => new Element(tag), title: '', querySelectorAll: (selector) => selector === '[data-route]' || selector === '.nav-item' ? routes : selector === '[data-mutation]' ? nodes().filter((node) => 'mutation' in node.dataset) : [] };
  globalThis.window = Object.assign(new EventTarget(), { xfin: api }); get('metadata-filter').value = 'all'; get('prep-count').value = '2';
  await import(`../.out/renderer/app.js?offlineApp=${++sequence}`); await settle();
  const click = (id) => get(id).dispatchEvent(new Event('click')); const navigate = async (route) => { routes.find((button) => button.dataset.route === route).dispatchEvent(new Event('click')); await settle(); };
  return { get, calls, nodes, click, navigate, event: (value) => { assert.equal(typeof onStatus, 'function'); onStatus(value); }, progress: (value) => progress(value), offline: () => progress({ operation: 'core', phase: 'error', message: '/private/core' }), statusUnsubscribed: () => statusUnsubscribed, generate: async () => { get('prep-form').dispatchEvent(new Event('submit', { cancelable: true })); await settle(); }, restore: () => { window.dispatchEvent(new Event('beforeunload')); globalThis.document = previousDocument; globalThis.window = previousWindow; } };
}

const offlineApi = (calls) => ({
  queryLibrary: async input => { calls.push(['query', input]); return {tracks:[tracks[1]],query:input.query??{genre:'House'},genres:['House'],matchedCount:1,totalCount:2,suppressedCount:0}; },
  searchPlaylists: async input => { calls.push(['search',input]); return []; }, comparePlaylists: async input => {calls.push(['compare',input]);return {comparison:'Local evidence'};},
  deletePlaylist: async input => {calls.push(['delete',input]);return {deletionId:'archive',name:'Set'};},
  listDeletedPlaylists: async()=>[{deletionId:'archive',name:'Set',trackCount:2,deletedAt:''}],restorePlaylist:async input=>{calls.push(['restore',input]);return {id:'2',name:'Restored',trackCount:2,createdAt:''};},
});
test('real app mounts offline Library filters and keeps complete library available to Prep',async()=>{
 const calls=[];const f=await fixture(offlineApi(calls));try{
   assert.equal(f.get('offline-library-apply').tagName,'button');f.get('offline-library-bpm_min').value='120';f.click('offline-library-apply');await settle();
   assert.equal(calls[0][0],'query');assert.equal(calls[0][1].query.bpm_min,120);assert.equal(f.get('library-total').textContent,'2');assert.match(f.get('library-visible-count').textContent,/1 pista/);
   f.click('offline-library-clear');assert.match(f.get('library-visible-count').textContent,/2 pistas/);
 }finally{f.restore();}
});
test('real app local saved search, confirmed remove, restart recovery refresh and restore are reachable without AI',async()=>{
 const calls=[];const f=await fixture(offlineApi(calls));try{
   await f.navigate('playlists');assert.equal(f.get('offline-saved-delete-1').tagName,'button');f.get('offline-saved-request').value='none';f.click('offline-saved-search');await settle();assert.equal(f.get('playlists-list').children.length,0);f.click('offline-saved-clear');await settle();
   f.click('offline-saved-delete-1');await settle();assert.ok(calls.some(([kind])=>kind==='delete'));assert.equal(f.get('playlists-list').children.length,0);
   f.click('offline-saved-recovery');await settle();assert.equal(f.get('offline-saved-restore-archive').disabled,false);f.click('offline-saved-restore-archive');await settle();assert.ok(calls.some(([kind])=>kind==='restore'));assert.match(text(f.get('playlists-list')),/Restored/);
 }finally{f.restore();}
});
