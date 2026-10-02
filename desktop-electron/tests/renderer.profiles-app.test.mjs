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
  await import(`../.out/renderer/app.js?profilesApp=${++sequence}`); await settle();
  const click = (id) => get(id).dispatchEvent(new Event('click')); const navigate = async (route) => { routes.find((button) => button.dataset.route === route).dispatchEvent(new Event('click')); await settle(); };
  return { get, calls, nodes, click, navigate, event: (value) => { assert.equal(typeof onStatus, 'function'); onStatus(value); }, progress: (value) => progress(value), offline: () => progress({ operation: 'core', phase: 'error', message: '/private/core' }), statusUnsubscribed: () => statusUnsubscribed, generate: async () => { get('prep-form').dispatchEvent(new Event('submit', { cancelable: true })); await settle(); }, restore: () => { window.dispatchEvent(new Event('beforeunload')); globalThis.document = previousDocument; globalThis.window = previousWindow; } };
}
test('startup reads summary only, successful rescan publishes metadata before one cancellable completion',async()=>{
  let finish,completed=0;const f=await fixture({completeProfiles:()=>{completed++;return new Promise(resolve=>finish=resolve);}});try{
    assert.equal(completed,0);assert.equal(f.calls.filter(([kind])=>kind==='profileStatus').length,1);assert.match(f.get('profiles-summary').textContent,/0.*2/);
    f.click('library-status-rescan');await settle();assert.equal(completed,1);assert.equal(f.get('library-total').textContent,'2');assert.equal(f.get('library-table').hidden,false);assert.equal(f.get('cancel-operation').hidden,false);assert.equal(f.get('library-status-rescan').disabled,true);assert.equal(f.get('profiles-retry').disabled,true);f.click('profiles-retry');f.click('library-status-rescan');assert.equal(completed,1);
    f.progress({operation:'profiles.complete',phase:'profiles',jobId:'job',stage:'danceability',current:1,total:2,readyCount:1,failedCount:0});assert.match(f.get('operation-label').textContent,/bailabilidad/i);assert.equal(f.get('operation-progress').value,1);assert.equal(f.get('operation-progress').max,2);
    finish(completion());await settle();assert.match(f.get('profiles-summary').textContent,/completos/i);assert.equal(f.get('audio-player').paused,true);assert.equal(f.get('library-status-rescan').disabled,false);assert.equal(completed,1);
  }finally{f.restore();}
});
test('cancelled and failed scans do not auto-complete; profile cancellation waits then keeps partial summary and explicit retry',async()=>{
  let finish,cancels=0,completed=0;const f=await fixture({rescanLibrary:async()=>({tracks,count:2,cancelled:true}),cancelCurrent:async()=>{cancels++;},completeProfiles:()=>{completed++;return new Promise(resolve=>finish=resolve);}});try{
    f.click('library-status-rescan');await settle();assert.equal(completed,0);f.click('profiles-retry');await settle();assert.equal(completed,1);f.click('cancel-operation');assert.equal(cancels,1);assert.equal(f.get('library-status-rescan').disabled,true);finish(completion({cancelled:true,status:profileStatus({state:'cancelled',readyCount:1,spectralReadyCount:2,danceabilityReadyCount:1,edgeReadyCount:1,pendingCount:1}),completeCount:2,incompleteCount:0}));await settle();assert.match(f.get('profiles-summary').textContent,/cancelad/i);assert.match(f.get('profiles-summary').textContent,/1.*2/);assert.equal(f.get('profiles-retry').disabled,false);assert.equal(completed,1);
  }finally{f.restore();}
});
test('profile retry invalidates derived reviews and watch changes cancel stale completion without clearing metadata',async()=>{
  let finish,cancels=0;const f=await fixture({cancelCurrent:async()=>{cancels++;},completeProfiles:()=>new Promise(resolve=>finish=resolve)});try{
    await f.generate();assert.equal(f.get('review-content').hidden,false);f.click('start-live');await settle();f.click('profiles-retry');await settle();assert.equal(f.get('review-content').hidden,true);assert.equal(f.get('live-content').hidden,true);f.event(status({revision:9,changeState:'changed'}));assert.equal(cancels,1);finish(completion());await settle();assert.match(f.get('profiles-summary').textContent,/escanea/i);assert.equal(f.get('library-total').textContent,'2');assert.equal(f.get('review-content').hidden,true);assert.equal(f.get('profiles-retry').disabled,true);
  }finally{f.restore();}
});
test('profile settings default/local edits/dirty close persist across navigation, save invalidates review without autoplay',async()=>{
  const f=await fixture();try{
    await f.generate();await f.navigate('preferences');assert.equal(f.get('profile-settings-cohesion').value,'0.5');f.get('profile-settings-cohesion').value='.8';f.get('profile-settings-cohesion').dispatchEvent(new Event('input'));assert.equal(f.calls.some(([kind])=>kind==='saveProfileSettings'),false);assert.equal(f.calls.filter(([kind])=>kind==='dirty').at(-1)[1],true);
    await f.navigate('library');await f.navigate('preferences');assert.equal(f.get('profile-settings-cohesion').value,'0.8');f.click('profile-settings-save');await settle();assert.deepEqual(f.calls.find(([kind])=>kind==='saveProfileSettings')[1],{revision:'a'.repeat(64),spectralCohesion:.8});assert.equal(f.get('review-content').hidden,true);assert.equal(f.calls.filter(([kind])=>kind==='dirty').at(-1)[1],false);assert.equal(f.get('audio-player').paused,true);
  }finally{f.restore();}
});
test('unavailable result is safe/retryable and core death disables profile operations',async()=>{
  const f=await fixture({completeProfiles:async()=>completion({status:profileStatus({state:'unavailable'}),completeCount:2,incompleteCount:0})});try{f.click('profiles-retry');await settle();assert.match(f.get('profiles-summary').textContent,/no disponibles/i);assert.equal(f.get('profiles-retry').disabled,false);f.offline();assert.equal(f.get('profiles-retry').disabled,true);assert.equal(f.get('profile-settings-save').disabled,true);assert.doesNotMatch(text(f.get('profiles-container')),/private|core/);}finally{f.restore();}
});
test('watch-triggered rescan clears the paused old dirty notification and completes exactly once',async()=>{
  let finish,completed=0;const f=await fixture({rescanLibrary:()=>new Promise(resolve=>finish=resolve),completeProfiles:async()=>{completed++;return completion();}});try{
    f.event(status({revision:3,changeState:'changed'}));f.click('library-status-rescan');f.event(status({revision:4,changeState:'changed',watchState:'paused',watchedCount:0}));f.event(status({revision:5,changeState:'clean',watchState:'active'}));finish({tracks,count:2,cancelled:false});await settle();assert.equal(completed,1);assert.match(f.get('profiles-summary').textContent,/completos/i);
  }finally{f.restore();}
});
test('failed rescan and cancelled folder picker never queue profiles',async()=>{
  const f=await fixture({rescanLibrary:async()=>{throw Error('/private/scan');},chooseLibrary:async()=>null});try{f.click('library-status-rescan');await settle();f.click('choose-library');await settle();assert.equal(f.calls.some(([kind])=>kind==='completeProfiles'),false);assert.doesNotMatch(f.get('operation-detail').textContent,/private/);}finally{f.restore();}
});
test('profile completion counts are independent from metadata completeness for unavailable or already profiled tracks',async()=>{
 const unavailable=await fixture({completeProfiles:async()=>completion({status:profileStatus({state:'unavailable'}),completeCount:2,incompleteCount:0})});try{unavailable.click('profiles-retry');await settle();assert.match(unavailable.get('profiles-summary').textContent,/no disponibles/i);assert.equal(unavailable.get('profiles-error').hidden,true);assert.equal(unavailable.get('library-ready').textContent,'2');}finally{unavailable.restore();}
 const incompleteTracks=tracks.map((track,index)=>index?{...track,energy:null}:track);const profiled=await fixture({listLibrary:async()=>({tracks:incompleteTracks,count:2}),completeProfiles:async()=>completion({tracks:incompleteTracks,completeCount:1,incompleteCount:1})});try{profiled.click('profiles-retry');await settle();assert.match(profiled.get('profiles-summary').textContent,/completos: 2 de 2/i);assert.equal(profiled.get('profiles-error').hidden,true);assert.equal(profiled.get('library-ready').textContent,'1');}finally{profiled.restore();}
});
