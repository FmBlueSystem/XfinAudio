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
  const routes = ['library', 'metadata', 'preferences', 'playlists', 'editor', 'review', 'live', 'serato'].map((route) => { const button = new Element('button'); button.dataset.route = route; return button; });
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
  globalThis.window = Object.assign(new EventTarget(), { xfin: api }); get('metadata-filter').value = 'all'; get('prep-count').value = '2';
  await import(`../.out/renderer/app.js?restoredApp=${++sequence}`); await settle();
  const click = (id) => get(id).dispatchEvent(new Event('click')); const navigate = async (route) => { routes.find((button) => button.dataset.route === route).dispatchEvent(new Event('click')); await settle(); };
  return { get, calls, nodes, click, navigate, event: (value) => { assert.equal(typeof onStatus, 'function'); onStatus(value); }, offline: () => progress({ operation: 'core', phase: 'error', message: '/private/core' }), statusUnsubscribed: () => statusUnsubscribed, generate: async () => { get('prep-form').dispatchEvent(new Event('submit', { cancelable: true })); await settle(); }, restore: () => { window.dispatchEvent(new Event('beforeunload')); globalThis.document = previousDocument; globalThis.window = previousWindow; } };
}
const metadata=()=>({totalTracks:2,completeCount:0,incompleteCount:2,gaps:{bpm:2,camelot_key:0,energy_level:0},yearCoverage:{withReleaseYear:0,withoutReleaseYear:2},tracks:tracks.map((track,index)=>({...track,missingFields:['bpm'],explanation:'Revisar BPM',releaseYear:null,locked:false,priority:index+1})),repairPlan:'Revisar fuentes',readOnly:true});
test('metadata worklist reaches existing Serato route with exact scope and safe worklist label, never commits',async()=>{
 const exports=[];const f=await fixture({getMetadataReport:async()=>metadata(),previewSeratoExport:async params=>{exports.push(params);return {previewId:'preview',sourceRevision:'r',filename:'Reparar.crate',destinationLabel:'_Serato_',trackCount:2,readiness:'needs_review',warnings:['Lista de trabajo de metadatos'],blockers:[],canCommit:true,tracks,backup:{required:false}};}});try{
  await f.navigate('metadata');f.click('metadata-worklist-export-serato');assert.equal(document.title,'XfinAudio · Exportar a Serato');assert.match(f.get('serato-export-source').textContent,/metadatos/i);assert.doesNotMatch(f.get('serato-export-source').textContent,/playlist guardada|selección revisada actual/i);
  f.click('serato-export-choose');await settle();f.click('serato-export-preview');await settle();assert.deepEqual(exports[0].source,{kind:'metadata',status:'incomplete',missingField:null,trackIds:tracks.map(track=>track.id)});assert.equal(f.get('audio-player').paused,true);assert.equal(f.calls.some(([kind])=>kind==='commit'),false);
 }finally{f.restore();}
});
test('watch changes invalidate stale metadata worklist export callback before another source can be prepared',async()=>{
 const f=await fixture({getMetadataReport:async()=>metadata()});try{await f.navigate('metadata');const oldButton=f.get('metadata-worklist-export-serato');f.event(status({revision:8,changeState:'changed'}));oldButton.dispatchEvent(new Event('click'));assert.equal(document.title,'XfinAudio · Metadatos');assert.equal(f.get('serato-export-setup').hidden,false);assert.match(f.get('serato-export-source').textContent,/Elige/);}finally{f.restore();}
});
test('Library exports only current bounded Complete or Incomplete scope and disables mixed/all',async()=>{
 for(const [filter,expected] of [['ready','complete'],['incomplete','incomplete']]){
  const selectedTracks=filter==='ready'?tracks:tracks.map(track=>({...track,energy:null}));const exports=[];
  const f=await fixture({listLibrary:async()=>({tracks:selectedTracks,count:2}),previewSeratoExport:async params=>{exports.push(params);return {previewId:'preview',sourceRevision:'r',filename:'Metadatos.crate',destinationLabel:'_Serato_',trackCount:2,readiness:'needs_review',warnings:[],blockers:[],canCommit:true,tracks:selectedTracks,backup:{required:false}};}});try{
   assert.equal(f.get('export-library-worklist').disabled,true);f.get('metadata-filter').value=filter;f.get('metadata-filter').dispatchEvent(new Event('change'));assert.equal(f.get('export-library-worklist').disabled,false);f.click('export-library-worklist');f.click('serato-export-choose');await settle();f.click('serato-export-preview');await settle();assert.deepEqual(exports[0].source,{kind:'metadata',status:expected,missingField:null,trackIds:selectedTracks.map(track=>track.id)});
   await f.navigate('library');f.get('library-search').value='not present';f.get('library-search').dispatchEvent(new Event('input'));assert.equal(f.get('export-library-worklist').disabled,true);f.event(status({revision:4,changeState:'changed'}));assert.equal(f.get('export-library-worklist').disabled,true);
  }finally{f.restore();}
 }
});
test('Library worklist never widens an offline filtered scope and refuses more than500 rows',async()=>{
 const exports=[];const f=await fixture({queryLibrary:async()=>({tracks:[tracks[1]],query:{},genres:[],matchedCount:1,totalCount:2,suppressedCount:0}),searchPlaylists:async()=>[],previewSeratoExport:async params=>{exports.push(params);return {previewId:'preview',sourceRevision:'r',filename:'Worklist.crate',destinationLabel:'_Serato_',trackCount:1,readiness:'needs_review',warnings:[],blockers:[],canCommit:true,tracks:[tracks[1]],backup:{required:false}};}});try{f.click('offline-library-apply');await settle();f.get('metadata-filter').value='ready';f.get('metadata-filter').dispatchEvent(new Event('change'));f.click('export-library-worklist');f.click('serato-export-choose');await settle();f.click('serato-export-preview');await settle();assert.deepEqual(exports[0].source.trackIds,[tracks[1].id]);}finally{f.restore();}
 const many=Array.from({length:501},(_,i)=>({...tracks[0],id:i.toString(16).padStart(64,'0')}));const large=await fixture({listLibrary:async()=>({tracks:many,count:many.length})});try{large.get('metadata-filter').value='ready';large.get('metadata-filter').dispatchEvent(new Event('change'));assert.equal(large.get('export-library-worklist').disabled,true);large.click('export-library-worklist');assert.notEqual(document.title,'XfinAudio · Exportar a Serato');}finally{large.restore();}
});
