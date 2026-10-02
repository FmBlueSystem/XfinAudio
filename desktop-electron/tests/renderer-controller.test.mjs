import assert from 'node:assert/strict';
import test from 'node:test';

class Element extends EventTarget {
  textContent = '';
  value = '';
  disabled = false;
  hidden = false;
  dataset = {};
  children = [];
  attrs = {};
  classes = new Set();
  classList = { toggle: (name, enabled) => { if (enabled) this.classes.add(name); else this.classes.delete(name); }, contains: (name) => this.classes.has(name) };
  setAttribute(name, value) { this.attrs[name] = value; }
  removeAttribute(name) { delete this.attrs[name]; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  closest() { return null; }
  focus() { document.activeElement=this; }
}
const tick = () => new Promise((resolve) => setImmediate(resolve));
let sequence = 0;
async function fixture(overrides = {}) {
  const elements = new Map();
  const get = (id) => { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  const oldDocument = globalThis.document;
  const oldWindow = globalThis.window;
  const mutations = ['choose-library', 'choose-library-empty', 'generate-prep', 'save-playlist', 'refresh-playlists', 'refresh-metadata'];
  get('prep-count').value = '2';
  get('metadata-filter').value = 'all';
  const routes = ['library', 'metadata', 'prep', 'review', 'serato', 'preferences', 'ai'].map((name) => { const button = new Element(); button.dataset.route = name; return button; });
  let progress;
  let generated;
  const tracks = [{ id: 'a', title: 'A', artist: 'Artist', bpm: 120, key: '8A', energy: 5, duration: 60 }, { id: 'b', title: 'B', artist: 'Artist', bpm: 122, key: '8A', energy: 6, duration: 60 }];
  const api = {
    listLibrary: async () => ({ tracks, count: 2 }),
    getMetadataReport: async () => ({ totalTracks: 2, completeCount: 2, incompleteCount: 0, gaps: { bpm: 0, camelot_key: 0, energy_level: 0 }, yearCoverage: { withReleaseYear: 0, withoutReleaseYear: 2 }, tracks: [], repairPlan: 'No gaps', readOnly: true }),
    onProgress: (callback) => { progress = callback; return () => {}; },
    generatePrep: async (input) => { generated = input; return { reviewId: 'fresh', tracks, warnings: [], blockers: [], name: input.name, variant: 'balanced', readiness: 'ready' }; },
    ...overrides,
  };
  globalThis.document = {
    getElementById: get,
    createElement: () => new Element(),
    querySelectorAll: (selector) => selector === '[data-mutation]' ? mutations.map(get) : selector === '[data-route]' || selector === '.nav-item' ? routes : [],
    title: '',
  };
  globalThis.window = Object.assign(new EventTarget(), { xfin: api });
  await import(`../.out/renderer/app.js?controllerTest=${++sequence}`);
  await tick();
  return { get, navigate: (name) => routes.find((button) => button.dataset.route === name).dispatchEvent(new Event('click')), progress: (event) => progress(event), generated: () => generated, restore: () => { globalThis.document = oldDocument; globalThis.window = oldWindow; } };
}

test('blank optional session name is normalized in the actual generate request', async () => {
  const fixtureState = await fixture();
  try {
    fixtureState.get('prep-form').dispatchEvent(new Event('submit', { cancelable: true }));
    await tick();
    assert.deepEqual(fixtureState.generated(), { targetTrackCount: 2, name: 'Sesión equilibrada' });
  } finally { fixtureState.restore(); }
});

test('idle core termination shows a persistent offline error and disables mutations', async () => {
  const fixtureState = await fixture();
  try {
    fixtureState.progress({ jobId: '', operation: 'core', phase: 'error', message: 'Core stopped' });
    assert.equal(fixtureState.get('operation-status').hidden, false);
    assert.equal(fixtureState.get('operation-label').textContent, 'Servicio local desconectado');
    assert.equal(fixtureState.get('operation-detail').textContent, 'El servicio local dejó de responder. Reinicia XfinAudio para volver a conectar.');
    for (const id of ['choose-library', 'generate-prep', 'save-playlist', 'refresh-playlists']) assert.equal(fixtureState.get(id).disabled, true);
    fixtureState.get('prep-form').dispatchEvent(new Event('submit', { cancelable: true }));
    await tick();
    assert.equal(fixtureState.generated(), undefined);
    assert.equal(fixtureState.get('operation-label').textContent, 'Servicio local desconectado');
  } finally { fixtureState.restore(); }
});

test('late pending-library success cannot hide core termination or re-enable mutations', async () => {
  let resolveLibrary;
  const fixtureState = await fixture({ listLibrary: () => new Promise((resolve) => { resolveLibrary = resolve; }) });
  try {
    fixtureState.progress({ operation: 'core', phase: 'error', message: 'Stopped while loading' });
    resolveLibrary({ tracks: [], count: 0 });
    await tick();
    assert.equal(fixtureState.get('operation-status').hidden, false);
    assert.equal(fixtureState.get('operation-label').textContent, 'Servicio local desconectado');
    assert.equal(fixtureState.get('choose-library').disabled, true);
    assert.equal(fixtureState.get('operation-progress').hidden, true);
  } finally { fixtureState.restore(); }
});


test('metadata navigation waits for pending library work then loads exactly once', async () => {
  let resolveLibrary; let requests = 0;
  const data = { totalTracks: 0, completeCount: 0, incompleteCount: 0, gaps: { bpm: 0, camelot_key: 0, energy_level: 0 }, yearCoverage: { withReleaseYear: 0, withoutReleaseYear: 0 }, tracks: [], repairPlan: 'No gaps', readOnly: true };
  const f = await fixture({ listLibrary: () => new Promise((resolve) => { resolveLibrary = resolve; }), getMetadataReport: async () => { requests++; return data; } });
  try {
    f.navigate('metadata'); assert.equal(requests, 0);
    resolveLibrary({ tracks: [], count: 0 }); await tick(); await tick();
    assert.equal(requests, 1); assert.equal(globalThis.document.title, 'XfinAudio · Metadatos');
    assert.equal(f.get('metadata-report-container').children.length, 5); await tick(); assert.equal(requests, 1);
  } finally { f.restore(); }
});

test('late metadata response cannot navigate back or replace a disconnected view', async () => {
  let resolveReport;
  const f = await fixture({ getMetadataReport: () => new Promise((resolve) => { resolveReport = resolve; }) });
  try {
    f.navigate('metadata'); f.navigate('library');
    f.progress({ operation: 'core', phase: 'error', message: 'Offline during metadata' });
    resolveReport({ totalTracks: 0, completeCount: 0, incompleteCount: 0, gaps: { bpm: 0, camelot_key: 0, energy_level: 0 }, yearCoverage: { withReleaseYear: 0, withoutReleaseYear: 0 }, tracks: [], repairPlan: 'No gaps', readOnly: true });
    await tick();
    assert.equal(globalThis.document.title, 'XfinAudio · Biblioteca');
    assert.equal(f.get('metadata-report-container').children.length, 0);
    assert.equal(f.get('operation-detail').textContent, 'El servicio local dejó de responder. Reinicia XfinAudio para volver a conectar.'); assert.equal(f.get('refresh-metadata').disabled, true);
  } finally { f.restore(); }
});


test('Create reveals invalid hidden duration and keeps its cap/value through navigation and retry',async()=>{
 const f=await fixture();try{
  const group=f.get('prep-duration');group.tagName='DETAILS';group.open=false;f.get('prep-minutes').parentElement=group;
  f.get('prep-count').value='7';f.get('prep-minutes').value='601';f.get('prep-minutes').dispatchEvent(new Event('input'));
  f.get('prep-form').dispatchEvent(new Event('submit',{cancelable:true}));await tick();
  assert.equal(f.generated(),undefined);assert.equal(group.open,true);assert.equal(document.activeElement,f.get('prep-minutes'));assert.match(f.get('prep-validation').textContent,/600/);
  f.get('prep-minutes').value='30';f.get('prep-minutes').dispatchEvent(new Event('input'));f.navigate('library');f.navigate('prep');
  assert.equal(f.get('prep-count').value,'7');assert.equal(f.get('prep-minutes').value,'30');assert.match(f.get('prep-sizing-summary').textContent,/30 minutos.*7 pistas/);
  f.get('prep-form').dispatchEvent(new Event('submit',{cancelable:true}));await tick();assert.equal(f.generated().targetTrackCount,7);assert.equal(f.generated().targetMinutes,30);
 }finally{f.restore();}
});
test('browser invalid event opens hidden ancestors before submit and does not generate',async()=>{
 const f=await fixture();try{
  const outer={tagName:'DETAILS',open:false,parentElement:null};const inner={tagName:'DETAILS',open:false,parentElement:outer};const field=f.get('prep-minutes');field.parentElement=inner;field.validationMessage='Hasta 600 minutos';
  field.dispatchEvent(new Event('invalid',{cancelable:true}));assert.equal(inner.open,true);assert.equal(outer.open,true);assert.equal(document.activeElement,field);assert.equal(f.generated(),undefined);
 }finally{f.restore();}
});
test('tool back restores metadata origin without replacing its loaded report and preserves Create draft',async()=>{
 let requests=0;const f=await fixture({getMetadataReport:async()=>{requests++;return {totalTracks:0,completeCount:0,incompleteCount:0,gaps:{bpm:0,camelot_key:0,energy_level:0},yearCoverage:{withReleaseYear:0,withoutReleaseYear:0},tracks:[],repairPlan:'Ready',readOnly:true};}});try{
  f.get('prep-name').value='Borrador';f.navigate('metadata');await tick();const children=f.get('metadata-report-container').children;
  f.navigate('serato');f.get('tool-back').dispatchEvent(new Event('click'));await tick();assert.equal(document.title,'XfinAudio · Metadatos');assert.equal(f.get('metadata-report-container').children,children);assert.equal(requests,1);assert.equal(f.get('prep-name').value,'Borrador');
  f.get('tool-back').dispatchEvent(new Event('click'));assert.equal(document.title,'XfinAudio · Biblioteca');
 }finally{f.restore();}
});
test('compact context reports changed library and profile failures with a direct details action',async()=>{
 let onStatus;const f=await fixture({getLibraryStatus:async()=>({revision:1,changeState:'clean',watchState:'active',rootCount:1,watchedCount:1}),onLibraryStatus:callback=>{onStatus=callback;return()=>{};}});try{
  await tick();onStatus({revision:2,changeState:'changed',watchState:'unavailable',rootCount:1,watchedCount:0});
  assert.equal(f.get('context-status').hidden,false);assert.match(f.get('context-status-copy').textContent,/cambios.*escanear/i);assert.match(f.get('context-status-copy').textContent,/vigilancia.*disponible/i);
  f.get('context-status-open').dispatchEvent(new Event('click'));assert.equal(document.title,'XfinAudio · Biblioteca');assert.equal(f.get('library-tools').open,true);
 }finally{f.restore();}
});
test('Back restores the mounted entry control and fallback focus without changing preserved fields',async()=>{
 const f=await fixture();try{
  f.get('prep-form').dispatchEvent(new Event('submit',{cancelable:true}));await tick();f.navigate('review');const trigger=f.get('export-review');trigger.focus();f.navigate('serato');f.get('tool-back').focus();f.get('tool-back').dispatchEvent(new Event('click'));
  assert.equal(document.title,'XfinAudio · Revisar y exportar');assert.equal(document.activeElement,trigger);
  trigger.focus();f.navigate('serato');trigger.isConnected=false;f.get('tool-back').focus();f.get('tool-back').dispatchEvent(new Event('click'));assert.equal(document.activeElement,f.get('main-content'));
 }finally{f.restore();}
});
test('persistent Settings navigation from its AI child returns to the original Library entry',async()=>{
 const f=await fixture();try{f.navigate('preferences');f.navigate('ai');f.navigate('preferences');f.get('tool-back').dispatchEvent(new Event('click'));assert.equal(document.title,'XfinAudio · Biblioteca');}finally{f.restore();}
});
test('cancelled destination after Back preserves cached metadata DOM; explicit refresh and library invalidation still reload',async()=>{
 let requests=0;let finish;let onStatus;const report={totalTracks:0,completeCount:0,incompleteCount:0,gaps:{bpm:0,camelot_key:0,energy_level:0},yearCoverage:{withReleaseYear:0,withoutReleaseYear:0},tracks:[],repairPlan:'Ready',readOnly:true};
 const f=await fixture({getMetadataReport:async()=>{requests++;return report;},chooseSeratoDestination:()=>new Promise(resolve=>{finish=resolve;}),onLibraryStatus:callback=>{onStatus=callback;return()=>{};}});try{
  f.navigate('metadata');await tick();const initial=f.get('metadata-report-container').children;const retained={query:'House',page:2,explanation:'track'};initial[0].retained=retained;
  f.navigate('serato');const nodes=node=>[node,...node.children.flatMap(nodes)];nodes(f.get('serato-container')).find(node=>node.id==='serato-export-choose').dispatchEvent(new Event('click'));f.get('tool-back').dispatchEvent(new Event('click'));finish(null);await tick();await tick();
  assert.equal(document.title,'XfinAudio · Metadatos');assert.equal(requests,1);assert.equal(f.get('metadata-report-container').children,initial);assert.equal(initial[0].retained,retained);
  f.get('refresh-metadata').dispatchEvent(new Event('click'));await tick();assert.equal(requests,2);assert.notEqual(f.get('metadata-report-container').children,initial);
  onStatus({revision:7,changeState:'changed',watchState:'active',rootCount:1,watchedCount:1});f.navigate('library');f.navigate('metadata');await tick();assert.equal(requests,3);
 }finally{f.restore();}
});
test('explicit routes reveal the task start; background updates and Tool Back keep their focus policy',async()=>{
 const f=await fixture();try{
  const main=f.get('main-content');let scrolls=0;main.scrollIntoView=options=>{assert.equal(options.block,'start');scrolls++;};f.get('prep-name').value='Preservar';f.navigate('prep');assert.equal(scrolls,1);assert.equal(document.activeElement,main);assert.equal(f.get('prep-name').value,'Preservar');
  f.get('library-search').dispatchEvent(new Event('input'));assert.equal(scrolls,1);f.navigate('metadata');await tick();assert.equal(scrolls,2);
  const trigger=f.get('refresh-metadata');trigger.focus();f.navigate('serato');assert.equal(scrolls,3);f.get('tool-back').dispatchEvent(new Event('click'));assert.equal(document.activeElement,trigger);assert.equal(scrolls,3);
 }finally{f.restore();}
});
