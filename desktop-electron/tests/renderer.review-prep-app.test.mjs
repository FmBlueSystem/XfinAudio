import assert from 'node:assert/strict';
import test from 'node:test';
class Element extends EventTarget {
  constructor(tag = 'div') { super(); this.tagName = tag; }
  get options() { return this.children.filter(node => node.tagName === 'option'); }
  get selectedOptions() { return this.options.filter(node => node.selected); }
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
const selectReviewTrack = (f, index) => { f.get('review-selected-track').value = tracks[index].id; f.get('review-selected-track').dispatchEvent(new Event('change')); };
const profileStatus = (patch = {}) => ({state:'partial',totalTracks:2,readyCount:0,spectralReadyCount:0,danceabilityReadyCount:0,edgeReadyCount:0,pendingCount:2,failedCount:0,...patch});
const completion = (patch = {}) => ({cancelled:false,tracks,status:profileStatus({state:'complete',readyCount:2,spectralReadyCount:2,danceabilityReadyCount:2,edgeReadyCount:2,pendingCount:0}),completeCount:2,incompleteCount:0,...patch});
const detailed=(patch={})=>({reviewId:'review',name:'Set',variant:'balanced',readiness:'ready',tracks,warnings:[],blockers:[],qualityScore:.8,engineFacts:'Local engine: 2 tracks',readinessSummary:'Ready',readinessChecks:[{label:'Metadata',status:'ready',detail:'Complete'}],transitions:[{index:1,leftTrackId:tracks[0].id,rightTrackId:tracks[1].id,totalScore:.8,compatibilityScore:.9,mixabilityScore:.7,components:{bpm:1,key:.8},explanations:['Compatible'],warnings:[]}],protectedTrackIds:[],...patch});
const prepSettings=(patch={})=>({revision:'a'.repeat(64),requiredTrackIds:[],excludedTrackIds:[],genreFocus:'House',unavailableRequiredCount:0,unavailableExcludedCount:0,...patch});
let sequence = 0;
async function fixture(overrides = {}) {
  const previousDocument = globalThis.document; const previousWindow = globalThis.window; const elements = new Map(); const calls = []; let onStatus; let progress; let statusUnsubscribed = false;
  const nodes = () => [...elements.values()].flatMap(all); const get = (id) => { const dynamic = nodes().find((node) => node.id === id); if (dynamic) return dynamic; if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  const routes = ['library', 'prep', 'preferences', 'playlists', 'editor', 'review', 'live', 'serato'].map((route) => { const button = new Element('button'); button.dataset.route = route; return button; });
  const api = {
    listLibrary: async () => { calls.push(['library']); return { tracks, count: 2 }; }, getPrepCatalog: async () => ({ strategies: [] }), onProgress: (callback) => { progress = callback; return () => {}; },
    getPreferences: async () => { calls.push(['preferences']); return prefs(); }, savePreferences: async (input) => { calls.push(['savePreferences', input]); return prefs({ ...input, revision: 'b'.repeat(64) }); },
    getLibraryStatus: async () => { calls.push(['status']); return status(); }, onLibraryStatus: (callback) => { onStatus = callback; return () => { statusUnsubscribed = true; }; },
    getProfileStatus: async () => { calls.push(['profileStatus']); return profileStatus(); }, getProfileSettings: async () => { calls.push(['profileSettings']); return {revision:'a'.repeat(64),spectralCohesion:.5}; }, saveProfileSettings: async (input) => {calls.push(['saveProfileSettings',input]);return {...input,revision:'b'.repeat(64)};}, completeProfiles: async () => {calls.push(['completeProfiles']);return completion();},
    rescanLibrary: async () => { calls.push(['rescan']); return { tracks, count: 2 }; }, setDraftDirty: async (dirty) => { calls.push(['dirty', dirty]); },
    listPlaylists: async () => [{ id: '1', name: 'Set', trackCount: 2, createdAt: '' }], openPlaylistEditor: async () => ({ id: '1', editId: 'edit', revision: 'r1', name: 'Set', tracks, missingTrackCount: 0 }), discardPlaylistEdit: async () => ({ id: '1', editId: 'edit', revision: 'r1', name: 'Set', tracks, missingTrackCount: 0 }),
    generatePrep: async (input) => {calls.push(['generate',input]);return detailed();},
    prepSettings: async()=>{calls.push(['prepSettings']);return prepSettings();},savePrepSettings:async(input)=>{calls.push(['savePrepSettings',input]);return prepSettings({...input,revision:'b'.repeat(64)});},
    reviewDetails:async(input)=>{calls.push(['reviewDetails',input]);return detailed();},reviewCompare:async(input)=>{calls.push(['reviewCompare',input]);return {reviewId:input.reviewId,available:true,replacement:tracks[1],original:detailed(),proposed:detailed(),message:'Preview only'};},reviewRemove:async(input)=>{calls.push(['reviewRemove',input]);return detailed({reviewId:'edited',tracks:[tracks[1]]});},reviewReorder:async(input)=>{calls.push(['reviewReorder',input]);return detailed({reviewId:'edited',tracks:[...tracks].reverse()});},
    selectPrepVariant: async (input) => { calls.push(['select', input]); return detailed({ reviewId: `variant-${input.variant}`, variant: input.variant }); },
    openPlaylist: async (input) => { calls.push(['open', input]); return detailed({ reviewId: 'opened', variant: 'saved', name: 'Set' }); },
    openLive: async () => ({ sessionId: 'live', revision: 0, sourceReviewId: 'review', state: 'active', current: tracks[0], history: [], candidates: [{ track: tracks[1], score: 1, alerts: [] }], elapsedSeconds: 0 }),
    chooseSeratoDestination: async () => ({ destinationId: 'dest', label: '_Serato_' }), previewSeratoExport: async () => ({ previewId: 'preview', sourceRevision: 'r', filename: 'Set.crate', destinationLabel: '_Serato_', trackCount: 2, readiness: 'ready', warnings: [], blockers: [], canCommit: true, tracks, backup: { required: false } }), ...overrides,
  };
  globalThis.document = { getElementById: get, createElement: (tag) => new Element(tag), title: '', querySelectorAll: (selector) => selector === '[data-route]' || selector === '.nav-item' ? routes : selector === '[data-mutation]' ? nodes().filter((node) => 'mutation' in node.dataset) : [] };
  globalThis.window = Object.assign(new EventTarget(), { xfin: api }); get('metadata-filter').value = 'all'; get('prep-count').value = '2';
  await import(`../.out/renderer/app.js?reviewPrepApp=${++sequence}`); await settle();
  const click = (id) => get(id).dispatchEvent(new Event('click')); const navigate = async (route) => { routes.find((button) => button.dataset.route === route).dispatchEvent(new Event('click')); await settle(); };
  return { get, calls, nodes, click, navigate, event: (value) => { assert.equal(typeof onStatus, 'function'); onStatus(value); }, progress: (value) => progress(value), offline: () => progress({ operation: 'core', phase: 'error', message: '/private/core' }), statusUnsubscribed: () => statusUnsubscribed, generate: async () => { get('prep-form').dispatchEvent(new Event('submit', { cancelable: true })); await settle(); }, restore: () => { window.dispatchEvent(new Event('beforeunload')); globalThis.document = previousDocument; globalThis.window = previousWindow; } };
}
test('actual app restores explicit persistent Prep controls then sends them through generate',async()=>{const f=await fixture({prepSettings:async()=>prepSettings({requiredTrackIds:[tracks[0].id],genreFocus:'Techno'})});try{await f.navigate('prep');assert.equal(f.get('prep-genre').value,'Techno');assert.equal(f.get('prep-required').selectedOptions[0].value,tracks[0].id);await f.generate();assert.equal(f.calls.find(([kind])=>kind==='generate')[1].genreFocus,'Techno');assert.deepEqual(f.calls.find(([kind])=>kind==='generate')[1].requiredTrackIds,[tracks[0].id]);assert.match(text(f.get('review-engine-facts')),/Local engine/);assert.match(text(f.get('review-transition-evidence')),/bpm/);}finally{f.restore();}});
test('actual app compares without mutation and editing changes current review through bounded API',async()=>{const f=await fixture();try{await f.generate();selectReviewTrack(f,1);f.click('review-compare-1');await settle();assert.deepEqual(f.calls.find(([kind])=>kind==='reviewCompare')[1],{reviewId:'review',trackId:tracks[1].id});assert.match(text(f.get('review-replacement-comparison')),/Preview only/);f.click('review-remove-1');await settle();assert.deepEqual(f.calls.find(([kind])=>kind==='reviewRemove')[1],{reviewId:'review',trackId:tracks[1].id});assert.match(f.get('review-track-count').textContent,/1 pistas/);assert.equal(f.get('audio-player').paused,true);}finally{f.restore();}});
test('actual app local Prep edits survive navigation, flag close protection and persist only on save',async()=>{const f=await fixture();try{await f.navigate('prep');f.get('prep-genre').value='Garage';f.get('prep-genre').dispatchEvent(new Event('input'));assert.equal(f.calls.filter(([kind])=>kind==='dirty').at(-1)[1],true);assert.equal(f.calls.some(([kind])=>kind==='savePrepSettings'),false);await f.navigate('library');await f.navigate('prep');assert.equal(f.get('prep-genre').value,'Garage');f.click('prep-settings-save');await settle();assert.equal(f.calls.find(([kind])=>kind==='savePrepSettings')[1].genreFocus,'Garage');assert.equal(f.calls.filter(([kind])=>kind==='dirty').at(-1)[1],false);}finally{f.restore();}});
test('clean persisted Prep choices survive rescan and automatic profile completion without writes or dirty flags',async()=>{let reads=0;const f=await fixture({prepSettings:async()=>{reads++;return prepSettings({requiredTrackIds:[tracks[0].id],excludedTrackIds:[tracks[1].id],genreFocus:'Deep House'});}});try{await f.navigate('prep');assert.equal(reads,1);assert.equal(f.get('prep-required').selectedOptions[0].value,tracks[0].id);f.click('library-status-rescan');await settle();await settle();assert.ok(f.calls.some(([kind])=>kind==='completeProfiles'));assert.ok(reads>=2);assert.equal(f.get('prep-required').selectedOptions[0].value,tracks[0].id);assert.equal(f.get('prep-excluded').selectedOptions[0].value,tracks[1].id);assert.equal(f.get('prep-genre').value,'Deep House');assert.equal(f.calls.some(([kind])=>kind==='savePrepSettings'),false);assert.equal(f.calls.filter(([kind])=>kind==='dirty').at(-1)[1],false);}finally{f.restore();}});
test('dirty missing Prep choices remain explicit until discard and authoritative restore',async()=>{let gone=false;const remaining=[tracks[1]];const f=await fixture({prepSettings:async()=>prepSettings(gone?{requiredTrackIds:[],genreFocus:'House',unavailableRequiredCount:1}:{requiredTrackIds:[tracks[0].id]}),rescanLibrary:async()=>{gone=true;return {tracks:remaining,count:1};},completeProfiles:async()=>completion({tracks:remaining,completeCount:1,incompleteCount:0,status:profileStatus({state:'complete',totalTracks:1,readyCount:1,spectralReadyCount:1,danceabilityReadyCount:1,edgeReadyCount:1,pendingCount:0})})});try{await f.navigate('prep');f.get('prep-genre').value='Unsaved Garage';f.get('prep-genre').dispatchEvent(new Event('input'));f.click('library-status-rescan');await settle();await settle();assert.equal(f.get('prep-genre').value,'Unsaved Garage');const missing=f.get('prep-required').selectedOptions[0];assert.equal(missing.value,tracks[0].id);assert.equal(missing.disabled,true);assert.match(missing.textContent,/No disponible/);assert.equal(f.calls.some(([kind])=>kind==='savePrepSettings'),false);assert.equal(f.calls.filter(([kind])=>kind==='dirty').at(-1)[1],true);f.click('prep-settings-discard');await settle();f.click('prep-settings-load');await settle();assert.equal(f.get('prep-required').selectedOptions.length,0);assert.equal(f.get('prep-genre').value,'House');assert.match(f.get('prep-settings-unavailable').textContent,/1 obligatorias/);assert.equal(f.calls.filter(([kind])=>kind==='dirty').at(-1)[1],false);}finally{f.restore();}});
test('same-ID evidence load preserves Live and Serato preview; explicit review mutation invalidates both',async()=>{const f=await fixture({generatePrep:async()=>{const value=detailed();delete value.transitions;delete value.readinessChecks;delete value.engineFacts;return value;}});try{await f.generate();f.click('start-live');await settle();assert.equal(f.get('live-content').hidden,false);f.click('export-review');await settle();f.click('serato-export-choose');await settle();f.click('serato-export-preview');await settle();assert.equal(f.get('serato-export-proposal').hidden,false);f.click('review-load-evidence');await settle();assert.equal(f.get('live-content').hidden,false);assert.equal(f.get('live-unavailable').hidden,true);assert.equal(f.get('serato-export-proposal').hidden,false);selectReviewTrack(f,1);f.click('review-remove-1');await settle();assert.equal(f.get('live-content').hidden,true);assert.equal(f.get('serato-export-proposal').hidden,true);}finally{f.restore();}});
const quickReceipt=(patch={})=>({receiptId:'receipt',filename:'Set.crate',destinationLabel:'_Serato_ · dd',trackCount:2,validated:true,backupCreated:false,...patch});
test('the review button exports to Serato in two actions, stays on the review screen and reveals the crate',async()=>{
 const sent=[],revealed=[];
 const f=await fixture({quickSeratoExport:async(input)=>{sent.push(input);return {status:'exported',receipt:quickReceipt()};},revealSeratoExport:async(input)=>{revealed.push(input);}});
 try{
  await f.generate();
  assert.equal(document.title,'XfinAudio · Revisar y exportar');
  f.click('export-review');await settle();
  assert.deepEqual(sent,[{source:{kind:'review',reviewId:'review'}}],'one click sends only the scoped source: the core names the crate');
  assert.equal(sent[0].source.destinationId,undefined);assert.equal(sent[0].confirmed,undefined);
  assert.equal(document.title,'XfinAudio · Revisar y exportar','the export must not leave the review screen');
  assert.equal(f.get('serato-quick-export').hidden,false);
  assert.equal(f.get('serato-quick-export-notice').textContent,'Crate «Set» exportado a Serato');
  assert.equal(f.get('serato-quick-export-reveal').hidden,false);
  f.click('serato-quick-export-reveal');await settle();
  assert.deepEqual(revealed,[{receiptId:'receipt'}]);
 }finally{f.restore();}
});
test('a saved playlist card exports in place and keeps the Serato page as the advanced option',async()=>{
 const sent=[];const receipt=quickReceipt();
 const f=await fixture({quickSeratoExport:async(input)=>{sent.push(input);return {status:'exported',receipt};}});
 try{
  await f.navigate('playlists');await settle();
  const card=f.nodes().find(node=>node.tagName==='button'&&node.textContent==='Exportar a Serato');
  assert.ok(card,'the saved playlist card offers the export');
  card.dispatchEvent(new Event('click'));await settle();
  assert.deepEqual(sent,[{source:{kind:'saved',playlistId:'1'},name:'Set'}]);
  assert.equal(document.title,'XfinAudio · Playlists guardadas','the card export must stay on the saved playlists screen');
  assert.equal(f.get('serato-quick-export-notice').textContent,'Crate «Set» exportado a Serato');
  f.click('serato-quick-export-advanced');await settle();
  assert.equal(document.title,'XfinAudio · Exportar a Serato','the advanced option opens the existing export page');
  assert.match(f.get('serato-export-source').textContent,/playlist guardada/i);
 }finally{f.restore();}
});
test('a blocked quick export shows the blockers, and a missing destination continues after the folder choice',async()=>{
 const sent=[];let step=0;
 const f=await fixture({quickSeratoExport:async(input)=>{sent.push(input);step+=1;
  if(step===1)return {status:'blocked',filename:'Set.crate',blockers:['Review sources or settings changed; generate a new review']};
  if(step===2)return {status:'needs_destination'};
  return {status:'exported',receipt:quickReceipt()};},
  chooseSeratoDestination:async()=>({destinationId:'dest',label:'_Serato_ · dd'})});
 try{
  await f.generate();
  f.click('export-review');await settle();
  assert.equal(f.get('serato-quick-export-notice').textContent,'No se exportó nada: la selección no está lista');
  assert.deepEqual(f.get('serato-quick-export-blockers').children.map(node=>node.textContent),['Review sources or settings changed; generate a new review']);
  assert.equal(f.get('serato-quick-export-reveal').hidden,true);
  assert.equal(document.title,'XfinAudio · Revisar y exportar');
  f.click('export-review');await settle();
  assert.equal(f.get('serato-quick-export-notice').textContent,'No se encontró la carpeta _Serato_ de destino');
  assert.equal(f.get('serato-quick-export-choose').hidden,false);
  f.click('serato-quick-export-choose');await settle();
  assert.equal(sent.length,3,'the folder choice continues to the same confirmation');
  assert.equal(f.get('serato-quick-export-notice').textContent,'Crate «Set» exportado a Serato');
  assert.equal(document.title,'XfinAudio · Revisar y exportar');
 }finally{f.restore();}
});
test('a validated receipt survives the local core stopping while the native dialog is open',async()=>{
 let finish;
 const f=await fixture({quickSeratoExport:()=>new Promise((resolve)=>{finish=resolve;})});
 try{
  await f.generate();f.click('export-review');await settle();
  f.offline();await settle();
  finish({status:'exported',receipt:quickReceipt()});await settle();await settle();
  assert.equal(f.get('serato-quick-export-notice').textContent,'Crate «Set» exportado a Serato','a completed write must keep its receipt');
  assert.equal(f.get('serato-quick-export-reveal').hidden,false);
 }finally{f.restore();}
});
test('cancelling the native dialog leaves a quiet note and no receipt to reveal',async()=>{
 const f=await fixture({quickSeratoExport:async()=>({status:'cancelled'})});
 try{
  await f.generate();f.click('export-review');await settle();
  assert.equal(f.get('serato-quick-export-notice').textContent,'Exportación cancelada');
  assert.equal(f.get('serato-quick-export-reveal').hidden,true);
  assert.equal(f.get('serato-quick-export-choose').hidden,true);
 }finally{f.restore();}
});
test('a supervised restart returns the app to its normal state and an exhausted one keeps the restart message',async()=>{
 const f=await fixture();
 try{
  await f.navigate('prep');
  assert.equal(f.get('generate-prep').disabled,false);
  f.offline();await settle();
  assert.equal(f.get('generate-prep').disabled,true,'a stopped core gates every action');
  assert.equal(f.get('operation-label').textContent,'Servicio local desconectado');
  f.progress({operation:'core',phase:'restarted',message:'El servicio local volvió a estar disponible.'});await settle();
  assert.equal(f.get('generate-prep').disabled,false,'a restarted core makes the app usable again without a manual restart');
  assert.equal(f.get('operation-label').textContent,'Servicio local disponible');
  assert.doesNotMatch(text(f.get('operation-status')),/Reinicia XfinAudio/);
  f.offline();await settle();
  assert.equal(f.get('generate-prep').disabled,true);
  assert.equal(f.get('operation-label').textContent,'Servicio local desconectado','restarts that run out keep the existing restart message');
 }finally{f.restore();}
});
test('a generated set exports and previews with the crate name the core proposes',async()=>{
 const sent=[];const previews=[];
 const receipt=quickReceipt({filename:'XfinAudio%%Build 6-jun.crate'});
 const f=await fixture({
  quickSeratoExport:async(input)=>{sent.push(input);return {status:'exported',receipt};},
  previewSeratoExport:async(input)=>{previews.push(input);return {previewId:'preview',sourceRevision:'r',filename:'XfinAudio%%Build 6-jun.crate',destinationLabel:'_Serato_ · dd',trackCount:2,readiness:'ready',warnings:[],blockers:[],canCommit:true,tracks,backup:{required:false}};},
 });
 try{
  await f.generate();
  f.click('export-review');await settle();
  assert.deepEqual(sent,[{source:{kind:'review',reviewId:'review'}}],'a generated set sends no crate name');
  assert.equal(f.get('serato-quick-export-notice').textContent,'Crate «XfinAudio%%Build 6-jun» exportado a Serato');
  assert.match(f.get('serato-quick-export-detail').textContent,/XfinAudio%%Build 6-jun\.crate/);
  f.click('serato-quick-export-advanced');await settle();
  assert.equal(document.title,'XfinAudio · Exportar a Serato');
  assert.equal(f.get('serato-export-name').value,'','the page starts from the automatic name, not from the set name');
  f.click('serato-export-choose');await settle();
  f.click('serato-export-preview');await settle();
  assert.deepEqual(previews,[{source:{kind:'review',reviewId:'review'},destinationId:'dest'}],'the page also sends no name');
  assert.match(text(f.get('serato-export-proposal')),/Archivo: XfinAudio%%Build 6-jun\.crate/,'the preview shows the crate name the core chose');
 }finally{f.restore();}
});
test('a name typed on the Serato page is used unchanged',async()=>{
 const previews=[];
 const f=await fixture({previewSeratoExport:async(input)=>{previews.push(input);return {previewId:'preview',sourceRevision:'r',filename:'Viernes 14-nov.crate',destinationLabel:'_Serato_ · dd',trackCount:2,readiness:'ready',warnings:[],blockers:[],canCommit:true,tracks,backup:{required:false}};}});
 try{
  await f.generate();
  f.click('export-review');await settle();
  f.click('serato-quick-export-advanced');await settle();
  f.get('serato-export-name').value='Viernes 14-nov';f.get('serato-export-name').dispatchEvent(new Event('input'));
  f.click('serato-export-choose');await settle();
  f.click('serato-export-preview');await settle();
  assert.deepEqual(previews,[{source:{kind:'review',reviewId:'review'},destinationId:'dest',name:'Viernes 14-nov'}]);
  assert.match(text(f.get('serato-export-proposal')),/Viernes 14-nov\.crate/);
 }finally{f.restore();}
});
const discardQuestion='Vas a descartar los cambios de esta lista. ¿Continuar?';
const variantButton=(f,name)=>f.nodes().find(node=>node.tagName==='button'&&node.dataset.variant===name);
const openPlaylistButton=(f)=>f.nodes().find(node=>node.tagName==='button'&&node.textContent==='Abrir playlist →');
const editReview=async(f)=>{selectReviewTrack(f,1);f.click('review-remove-1');await settle();assert.equal(f.get('review-track-count').textContent,'1 pistas · 2:00');};
const plan=()=>({planId:'plan',variants:['safe','balanced','adventurous'].map((name)=>({name,description:`Motor ${name}`,trackCount:2,warnings:[],blockers:[],readiness:'ready',qualityScore:.8}))});
test('an edited review asks before generating again and «Seguir editando» changes nothing',async()=>{
 const f=await fixture();
 try{
  await f.generate();
  assert.equal(f.get('discard-guard').open,false,'a fresh review needs no question');
  await editReview(f);
  const route=document.title;const calls=f.calls.length;
  await f.generate();
  assert.equal(f.calls.filter(([kind])=>kind==='generate').length,1,'nothing is generated while the question is open');
  const dialog=f.get('discard-guard');
  assert.equal(dialog.open,true);
  assert.equal(f.get('discard-guard-message').textContent,discardQuestion);
  assert.equal(f.get('discard-guard-confirm').textContent,'Descartar cambios');
  assert.equal(f.get('discard-guard-cancel').textContent,'Seguir editando');
  f.click('discard-guard-cancel');await settle();
  assert.equal(dialog.open,false);
  assert.equal(f.calls.length,calls,'«Seguir editando» calls nothing');
  assert.equal(document.title,route,'the route is unchanged');
  assert.equal(f.get('review-track-count').textContent,'1 pistas · 2:00','the edited review is untouched');
  await f.generate();
  assert.equal(dialog.open,true);
  assert.equal(f.calls.filter(([kind])=>kind==='generate').length,1);
  f.click('discard-guard-confirm');await settle();
  assert.equal(dialog.open,false);
  assert.equal(f.calls.filter(([kind])=>kind==='generate').length,2,'«Descartar cambios» generates');
  await f.generate();
  assert.equal(dialog.open,false,'the generated review is the new baseline');
  assert.equal(f.calls.filter(([kind])=>kind==='generate').length,3);
 }finally{f.restore();}
});
test('an edited review asks before another variant and «Seguir editando» keeps it',async()=>{
 const f=await fixture({generatePrep:async(input)=>{f.calls.push(['generate',input]);return detailed(plan());}});
 try{
  await f.generate();
  await editReview(f);
  variantButton(f,'safe').dispatchEvent(new Event('click'));await settle();
  assert.equal(f.get('discard-guard').open,true);
  assert.equal(f.get('discard-guard-message').textContent,discardQuestion);
  assert.equal(f.calls.some(([kind])=>kind==='select'),false,'no variant is opened while the question is open');
  f.click('discard-guard-cancel');await settle();
  assert.equal(f.calls.some(([kind])=>kind==='select'),false);
  assert.equal(f.get('review-track-count').textContent,'1 pistas · 2:00');
  variantButton(f,'safe').dispatchEvent(new Event('click'));await settle();
  f.click('discard-guard-confirm');await settle();
  assert.deepEqual(f.calls.find(([kind])=>kind==='select')[1],{planId:'plan',variant:'safe'});
  assert.equal(f.get('review-variant').textContent,'SELECCIÓN SEGURA');
  variantButton(f,'adventurous').dispatchEvent(new Event('click'));await settle();
  assert.equal(f.get('discard-guard').open,false,'the chosen variant is the new baseline');
 }finally{f.restore();}
});
test('an edited review asks before opening a saved playlist and discards only when confirmed',async()=>{
 const f=await fixture();
 try{
  await f.generate();
  await editReview(f);
  await f.navigate('playlists');
  const route=document.title;
  openPlaylistButton(f).dispatchEvent(new Event('click'));await settle();
  assert.equal(f.get('discard-guard').open,true);
  assert.equal(f.get('discard-guard-message').textContent,discardQuestion);
  assert.equal(f.calls.some(([kind])=>kind==='open'),false,'no playlist is opened while the question is open');
  f.click('discard-guard-cancel');await settle();
  assert.equal(f.calls.some(([kind])=>kind==='open'),false);
  assert.equal(document.title,route,'the route stays on the saved playlists');
  assert.equal(f.get('review-track-count').textContent,'1 pistas · 2:00');
  openPlaylistButton(f).dispatchEvent(new Event('click'));await settle();
  f.click('discard-guard-confirm');await settle();
  assert.deepEqual(f.calls.find(([kind])=>kind==='open')[1],{playlistId:'1'});
  assert.equal(document.title,'XfinAudio · Revisar y exportar');
  assert.equal(f.get('review-track-count').textContent,'2 pistas · 4:00','the opened playlist replaces the edited review');
 }finally{f.restore();}
});
