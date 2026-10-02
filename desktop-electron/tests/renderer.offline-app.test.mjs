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
  globalThis.document = { getElementById: get, createElement: (tag) => new Element(tag), title: '', querySelectorAll: (selector) => selector === '[data-route]' || selector === '.nav-item' ? routes : selector === '[data-library-sort]' ? nodes().filter(node=>'librarySort' in node.dataset) : selector === '[data-track-id]' ? nodes().filter(node=>'trackId' in node.dataset) : selector === '[data-mutation]' ? nodes().filter((node) => 'mutation' in node.dataset) : [] };
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

const columnFields=['title','artist','genre','bpm','key','energy','duration','format','bitrate'];
const audioTracks=[
 {...tracks[0],title:'Alpha',genre:'House',audioFormat:'MP4',audioCodec:'ALAC',bitrateKbps:705.6,bitrateMode:null},
 {...tracks[1],title:'Beta',genre:'House',audioFormat:'MP3',audioCodec:null,bitrateKbps:128,bitrateMode:'VBR'},
 {...tracks[0],id:'c'.repeat(64),title:'Unknown',audioFormat:null,bitrateKbps:null},
];
const resultFor=(rows,input)=>({tracks:rows,query:input.query??{},genres:['House'],matchedCount:rows.length,totalCount:rows.length,suppressedCount:0});
test('whole Library displays verified audio facts and accessible sortable headers for each data column',async()=>{
 const calls=[];const f=await fixture({...offlineApi(calls),listLibrary:async()=>({tracks:audioTracks,count:3})});try{
  const table=f.get('library-table').children[0],head=table.children[0].children[0];
  assert.equal(head.children.length,11);assert.equal(f.get('offline-library-sort').children[0].disabled,true);
  for(const field of columnFields){const button=f.nodes().find(n=>n.id==='library-sort-'+field);assert.ok(button,field);assert.equal(button.tagName,'button');assert.equal(button.type,'button');assert.match(button.attrs['aria-label'],/Ordenar/);}
  assert.equal(head.children[0].children.length,0);assert.equal(head.children.at(-1).children.length,0);
  assert.match(text(table),/MP4 · ALAC/);assert.match(text(table),/MP3/);assert.match(text(table),/705,6 kbps/);assert.match(text(table),/128 kbps · VBR/);assert.match(text(table),/No disponible/);assert.match(text(head),/BITRATE DECLARADO/);
 }finally{f.restore();}
});
test('each Library header dispatches one shared global ascending/descending order and synchronizes controls',async()=>{
 const calls=[];const f=await fixture({...offlineApi(calls),queryLibrary:async input=>{calls.push(['query',input]);return resultFor(input.descending?[tracks[1],tracks[0]]:tracks,input);}});try{
  for(const field of columnFields){
   for(const descending of [false,true]){f.click('library-sort-'+field);await settle();const request=calls.at(-1)[1];assert.equal(request.sortBy,field);assert.equal(request.descending,descending);assert.equal(f.get('offline-library-sort').value,field);assert.equal(f.get('offline-library-descending').checked,descending);const header=f.get('library-table').children[0].children[0].children[0].children.find(th=>th.children.some(n=>n.id==='library-sort-'+field));assert.equal(header.attrs['aria-sort'],descending?'descending':'ascending');assert.match(text(header),descending?/↓/:/↑/);assert.equal(f.get('library-table').children[0].children[1].children[0].children[1].children[0].textContent,descending?'b':'a');}
  }
  f.get('offline-library-sort').value='bitrate';f.get('offline-library-descending').checked=false;f.click('offline-library-apply');await settle();assert.match(text(f.get('library-sort-bitrate')),/↑/);
 }finally{f.restore();}
});
test('global header ordering preserves active filters, preview and Prep selection across all rows',async()=>{
 const rows=Array.from({length:650},(_,i)=>({...tracks[0],id:i.toString(16).padStart(64,'0'),title:'Track '+i,genre:'House',bitrateKbps:i+1}));const calls=[];
 const f=await fixture({...offlineApi(calls),listLibrary:async()=>({tracks:rows,count:rows.length}),queryLibrary:async input=>{calls.push(['query',input]);return resultFor(input.descending?[...rows].reverse():rows,input);}});try{
  f.get('offline-library-genre').value='House';f.get('offline-library-duplicates').checked=true;f.click('offline-library-apply');await settle();
  f.get('library-search').value='Track 6';f.get('library-search').dispatchEvent(new Event('input'));f.get('metadata-filter').value='ready';f.get('metadata-filter').dispatchEvent(new Event('change'));
  f.get('prep-start').value=rows[6].id;const play=f.nodes().find(n=>n.dataset.trackId===rows[6].id);play.dispatchEvent(new Event('click'));await settle();f.get('audio-player').currentTime=42;const source=f.get('audio-player').src;
  f.get('offline-library-genre').value='Unsaved edit';f.click('library-sort-bitrate');await settle();f.click('library-sort-bitrate');await settle();
  assert.deepEqual(calls.at(-1)[1].query,{genre:'House'});assert.equal(calls.at(-1)[1].hideDuplicates,true);assert.equal(f.get('offline-library-genre').value,'Unsaved edit');assert.equal(f.get('library-search').value,'Track 6');assert.equal(f.get('metadata-filter').value,'ready');
  const rendered=f.get('library-table').children[0].children[1].children;assert.equal(rendered.length,61);assert.equal(rendered[0].children[1].children[0].textContent,'Track 649');assert.equal(f.get('prep-start').value,rows[6].id);assert.equal(f.get('audio-player').src,source);assert.equal(f.get('audio-player').currentTime,42);assert.equal(f.get('audio-player').paused,false);
 }finally{f.restore();}
});
test('failed global sorting retains the last successful order and stale replies cannot overwrite a refreshed Library',async()=>{
 let reject=false,resolve;const calls=[];const f=await fixture({...offlineApi(calls),queryLibrary:async input=>{calls.push(['query',input]);if(reject)throw new Error('failed');if(input.sortBy==='format')return new Promise(r=>resolve=r);return resultFor(tracks,input);}});try{
  f.click('library-sort-bpm');await settle();reject=true;f.click('library-sort-bitrate');await settle();assert.match(text(f.get('library-sort-bpm')),/↑/);assert.doesNotMatch(text(f.get('library-sort-bitrate')),/[↑↓]/);assert.equal(f.get('offline-library-sort').value,'bpm');
  reject=false;f.click('library-sort-format');await settle();f.click('library-sort-energy');assert.equal(calls.at(-1)[1].sortBy,'format');f.event(status({revision:2,changeState:'changed'}));resolve(resultFor([tracks[1]],{}));await settle();assert.match(f.get('library-visible-count').textContent,/2 pistas/);assert.doesNotMatch(text(f.get('library-sort-format')),/[↑↓]/);
 }finally{f.restore();}
});
