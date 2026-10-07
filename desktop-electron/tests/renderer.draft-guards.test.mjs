import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { LoudnessHost } from '../.out/main/loudness-host.js';
class Element extends EventTarget {
  constructor(tag = 'div') { super(); this.tagName = tag; }
  get options() { return this.children.filter(node => node.tagName === 'option'); }
  get selectedOptions() { return this.options.filter(node => node.selected); }
  textContent = ''; value = ''; checked = false; disabled = false; hidden = false; dataset = {}; children = []; attrs = {}; classes = new Set(); paused = true; duration = 0; currentTime = 0;
  classList = { toggle: (key, active) => active ? this.classes.add(key) : this.classes.delete(key), contains: (key) => this.classes.has(key) };
  setAttribute(key, value) { this.attrs[key] = value; } removeAttribute(key) { delete this.attrs[key]; }
  append(...nodes) { this.children.push(...nodes); } replaceChildren(...nodes) { this.children = nodes; } closest() { return null; } focus() { document.activeElement = this; this.focusCount = (this.focusCount ?? 0) + 1; } pause() { this.paused = true; } load() {} async play() { this.paused = false; }
}
const all = (node) => [node, ...node.children.flatMap(all)]; const text = (node) => [node.textContent, ...node.children.map(text)].join(' ');
const tick = () => new Promise((resolve) => setImmediate(resolve)); const settle = async () => { for (let i = 0; i < 5; i++) await tick(); };
const prefs = (patch = {}) => ({ revision: 'a'.repeat(64), previewVolume: .25, watchLibrary: true, recoveryWarning: false, libraryLabels: ['DJ'], capabilities: { loudnessWriteback: false, providers: false, language: 'es' }, ...patch });
const status = (patch = {}) => ({ revision: 1, changeState: 'restored', watchState: 'active', rootCount: 1, watchedCount: 1, ...patch });
const tracks = ['a', 'b'].map((id) => ({ id: id.repeat(64), title: id, artist: 'DJ', bpm: 120, key: '8A', energy: 5, duration: 120, missing: false }));
const loudness = (patch = {}) => ({ revision: 'a'.repeat(64), enabled: true, targetLufs: -10, toleranceLu: 2, available: true, reason: 'ready', totalTracks: tracks.length, tracks: tracks.map((track) => ({ track, state: 'unmeasured', complete: false, lufs: null, lra: null, truePeak: null })), ...patch });
const receipt = (patch = {}) => ({ cancelled: false, changedCount: 1, unchangedCount: 1, failureCount: 0, backupCount: 1, status: loudness(), ...patch });
let sequence = 0;
async function fixture(overrides = {}) {
  const previousDocument = globalThis.document; const previousWindow = globalThis.window; const elements = new Map(); const calls = []; let onStatus; let progress; let statusUnsubscribed = false;
  const nodes = () => [...elements.values()].flatMap(all); const get = (id) => { const dynamic = nodes().find((node) => node.id === id); if (dynamic) return dynamic; if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  const routes = ['library', 'prep', 'ai', 'preferences', 'loudness', 'playlists', 'editor', 'review', 'live', 'serato'].map((route) => { const button = new Element('button'); button.dataset.route = route; return button; });
  const api = {
    getLoudnessStatus: async () => { calls.push(['loudness']); return loudness(); },
    saveLoudnessSettings: async (input) => { calls.push(['saveLoudness', input]); return loudness({ ...input, revision: 'b'.repeat(64) }); },
    previewLoudness: async (input) => { calls.push(['previewLoudness', input]); return { previewId: '12345678-1234-4123-8123-123456789012', trackCount: input.trackIds.length, backupBytes: 2048, force: input.force, replaceComments: true, tracks: tracks.filter((track) => input.trackIds.includes(track.id)) }; },
    runLoudness: async (input) => { calls.push(['runLoudness', input]); return receipt(); },
    cancelCurrent: async () => { calls.push(['cancel']); },
    listLibrary: async () => { calls.push(['library']); return { tracks, count: 2 }; }, getPrepCatalog: async () => ({ strategies: [] }), onProgress: (callback) => { progress = callback; return () => {}; },
    getPreferences: async () => { calls.push(['preferences']); return prefs(); }, savePreferences: async (input) => { calls.push(['savePreferences', input]); return prefs({ ...input, revision: 'b'.repeat(64) }); },
    getLibraryStatus: async () => { calls.push(['status']); return status(); }, onLibraryStatus: (callback) => { onStatus = callback; return () => { statusUnsubscribed = true; }; },
    rescanLibrary: async () => { calls.push(['rescan']); return { tracks, count: 2 }; }, setDraftDirty: async (dirty) => { calls.push(['dirty', dirty]); },
    listPlaylists: async () => [{ id: '1', name: 'Set', trackCount: 2, createdAt: '' }], openPlaylistEditor: async () => ({ id: '1', editId: 'edit', revision: 'r1', name: 'Set', tracks, missingTrackCount: 0 }), discardPlaylistEdit: async () => ({ id: '1', editId: 'edit', revision: 'r1', name: 'Set', tracks, missingTrackCount: 0 }),
    generatePrep: async () => ({ reviewId: 'review', name: 'Set', variant: 'balanced', readiness: 'ready', tracks, warnings: [], blockers: [] }),
    openLive: async () => ({ sessionId: 'live', revision: 0, sourceReviewId: 'review', state: 'active', current: tracks[0], history: [], candidates: [{ track: tracks[1], score: 1, alerts: [] }], elapsedSeconds: 0 }),
    chooseSeratoDestination: async () => ({ destinationId: 'dest', label: '_Serato_' }), previewSeratoExport: async () => ({ previewId: 'preview', sourceRevision: 'r', filename: 'Set.crate', destinationLabel: '_Serato_', trackCount: 2, readiness: 'ready', warnings: [], blockers: [], canCommit: true, tracks, backup: { required: false } }), ...overrides,
  };
  globalThis.document = { getElementById: get, createElement: (tag) => new Element(tag), title: '', querySelectorAll: (selector) => selector === '[data-route]' || selector === '.nav-item' ? routes : selector === '[data-mutation]' ? nodes().filter((node) => 'mutation' in node.dataset) : selector === '[data-track-id]' ? nodes().filter((node) => 'trackId' in node.dataset) : [] };
  globalThis.window = Object.assign(new EventTarget(), { xfin: api }); get('metadata-filter').value = 'all'; get('prep-count').value = '2';
  await import(`../.out/renderer/app.js?dirtyBoundary=${++sequence}`); await settle();
  const click = (id) => get(id).dispatchEvent(new Event('click')); const navigate = async (route) => { routes.find((button) => button.dataset.route === route).dispatchEvent(new Event('click')); await settle(); };
  return { get, calls, nodes, click, navigate, progress: (event) => progress(event), event: (value) => { assert.equal(typeof onStatus, 'function'); onStatus(value); }, offline: () => progress({ operation: 'core', phase: 'error', message: '/private/core' }), statusUnsubscribed: () => statusUnsubscribed, generate: async () => { get('prep-form').dispatchEvent(new Event('submit', { cancelable: true })); await settle(); }, restore: () => { window.dispatchEvent(new Event('beforeunload')); globalThis.document = previousDocument; globalThis.window = previousWindow; } };
}

// Execute the current production main-process guard verbatim, rather than a permissive mock.
// The real LoudnessHost owns preview tokens/native confirmation after this IPC boundary.
const mainSource = readFileSync(new URL('../src/main.ts', import.meta.url), 'utf8');
const guardLine = mainSource.split('\n').find(line => line.includes("if(draftDirty&&['previewLoudness','runLoudness']"));
assert.ok(guardLine, 'main loudness draft guard must be represented by this fixture');
const enforceMainGuard = new Function('draftDirty', 'method', guardLine);
const prepSnapshot = patch => ({revision:'a'.repeat(64), requiredTrackIds:[], excludedTrackIds:[], genreFocus:'', unavailableRequiredCount:0, unavailableExcludedCount:0, ...patch});
const aiSnapshot = patch => ({revision:'a'.repeat(64), enabled:false, provider:'nan', credentialLabel:null, configured:false, recipient:'https://api.nan.builders/v1/chat/completions', ...patch});
async function guardedFixture(previewWait) {
  let dirty = false; const boundary = []; const core = []; let confirms = 0;
  const host = new LoudnessHost({isClosing:()=>false, cancel:async()=>({cancelled:false}), confirm:async()=>{confirms++;return false;}, request:async(method,input)=>{
    core.push([method,input]);
    if(method==='loudness.preview') { if(previewWait) await previewWait; return {previewId:'12345678-1234-4123-8123-123456789012',trackCount:input.trackIds.length,backupBytes:2048,force:input.force,replaceComments:true,tracks:tracks.filter(track=>input.trackIds.includes(track.id))}; }
    if(method==='loudness.confirmation') return {trackCount:1};
    if(method==='loudness.status') return loudness();
    throw Error('Unexpected synthetic core request: '+method);
  }});
  const invoke = async(method,input) => { boundary.push([method,input]); enforceMainGuard(dirty,method); return method==='previewLoudness'?host.preview(input):host.run(input.previewId); };
  const f = await fixture({
    setDraftDirty:async value=>{dirty=value;boundary.push(['setDraftDirty',value]);},
    previewLoudness:input=>invoke('previewLoudness',input), runLoudness:input=>invoke('runLoudness',input),
    previewLegacyImport:async()=>{boundary.push(['previewLegacyImport']);return null;},applyLegacyImport:async()=>{throw Error('Unexpected import');},discardLegacyImport:async()=>({discarded:true}),
    queryLibrary:async()=>({tracks,query:{},genres:[],matchedCount:2,totalCount:2,suppressedCount:0}),searchPlaylists:async()=>[],comparePlaylists:async()=>({comparison:''}),deletePlaylist:async input=>{boundary.push(['deletePlaylist',input]);if(dirty)throw Error('[dirty_saved_draft]');return {cancelled:true};},listDeletedPlaylists:async()=>[],restorePlaylist:async()=>{throw Error('Unexpected restore');},
    getProfileSettings:async()=>({revision:'a'.repeat(64),spectralCohesion:.5}), saveProfileSettings:async input=>({...input,revision:'b'.repeat(64)}),
    prepSettings:async()=>prepSnapshot(), savePrepSettings:async input=>prepSnapshot({...input,revision:'b'.repeat(64)}),
    getAiStatus:async()=>aiSnapshot(), saveAiSettings:async input=>aiSnapshot({...input,revision:'b'.repeat(64)}),
    chooseAiCredential:async()=>aiSnapshot(),clearAiCredential:async()=>aiSnapshot(),prepareAiRequest:async()=>{throw Error('Provider forbidden');},inspectAiPayload:async()=>{throw Error('Provider forbidden');},runAiRequest:async()=>{throw Error('Provider forbidden');},applyAiSuggestion:async()=>{throw Error('Provider forbidden');},
  });
  return {...f,boundary,core,dirty:()=>dirty,confirms:()=>confirms};
}
const scopes = [
  {name:'playlist editor',key:'editor',route:'editor',id:'editor-name',event:'input',value:'Pendiente',discard:'editor-discard',save:'editor-save',words:/editor/i},
  {name:'preferences',key:'preferences',route:'preferences',id:'preferences-volume',event:'input',value:'.4',discard:'preferences-discard',save:'preferences-save',words:/preferencias/i},
  {name:'profile cohesion',key:'profile',route:'preferences',id:'profile-settings-cohesion',event:'input',value:'.7',discard:'profile-settings-discard',save:'profile-settings-save',words:/cohesi[oó]n|perfiles/i},
  {name:'Prep controls',key:'prep',route:'prep',id:'prep-genre',event:'input',value:'Garage',discard:'prep-settings-discard',save:'prep-settings-save',words:/preparaci[oó]n|controles/i},
  {name:'loudness settings',key:'loudness',route:'loudness',id:'loudness-target',event:'change',value:'-14',discard:'loudness-discard',save:'loudness-save',words:/sonoridad/i},
  {name:'AI settings',key:'ai',route:'ai',id:'optional-ai-enabled',event:'change',value:true,discard:'optional-ai-discard',save:'optional-ai-save',words:/\bIA\b/i},
];
async function editScope(f,scope){if(scope.route==='editor'){await f.navigate('playlists');f.nodes().find(node=>node.tagName==='button'&&node.textContent==='Editar').dispatchEvent(new Event('click'));await settle();}await f.navigate(scope.route);const field=f.get(scope.id);assert.equal(field.disabled,false);if(typeof scope.value==='boolean')field.checked=scope.value;else field.value=scope.value;field.dispatchEvent(new Event(scope.event));await settle();assert.equal(f.dirty(),true,scope.name+' must reach main dirty state');await f.navigate('loudness');}
const reanalyze = f => f.get('loudness-reanalyze-'+tracks[0].id);
for(const scope of scopes) test(scope.name+' disables only loudness write actions, explains the scope and links to its preserved draft',async()=>{
  const f=await guardedFixture();try{
    assert.equal(f.dirty(),false);await editScope(f,scope);f.click('loudness-select-page');
    assert.equal(reanalyze(f).disabled,true);assert.equal(f.get('loudness-preview').disabled,true);assert.equal(f.get('loudness-run').disabled,true);
    assert.equal(f.get('loudness-draft-notice').hidden,false);assert.match(text(f.get('loudness-draft-notice')),scope.words);
    reanalyze(f).dispatchEvent(new Event('click'));await settle();assert.equal(f.boundary.filter(([method])=>method==='previewLoudness').length,0);assert.equal(f.core.length,0);
    const outer={tagName:'DETAILS',open:false,parentElement:null};const inner={tagName:'DETAILS',open:false,parentElement:outer};f.get(scope.id).parentElement=inner;
    f.click('loudness-draft-resolve-'+scope.key);await settle();assert.equal(outer.open,true);assert.equal(inner.open,true);assert.equal(document.activeElement,f.get(scope.id));if(scope.key==='prep')assert.equal(f.get('prep-saved-controls').open,true);assert.equal(f.get(scope.discard).disabled,false);assert.equal(f.get(scope.save).disabled,false);assert.equal(f.dirty(),true);
    assert.equal(typeof scope.value==='boolean'?f.get(scope.id).checked:f.get(scope.id).value,typeof scope.value==='boolean'?scope.value:scope.value.startsWith('.')?'0'+scope.value:scope.value);
    await assert.rejects(window.xfin.previewLoudness({trackIds:[tracks[0].id],force:true}),/dirty_draft/);await assert.rejects(window.xfin.runLoudness({previewId:'12345678-1234-4123-8123-123456789012'}),/dirty_draft/);assert.equal(f.core.length,0);assert.equal(f.confirms(),0);
    f.click(scope.discard);await settle();assert.equal(f.dirty(),false);await f.navigate('loudness');reanalyze(f).dispatchEvent(new Event('click'));await settle();assert.equal(f.get('loudness-preview-section').hidden,false);assert.equal(f.core.length,1);assert.equal(f.confirms(),0);
  }finally{f.restore();}
});
test('an existing preview cannot run while another draft is pending, and resumes after explicit discard',async()=>{
  const f=await guardedFixture();try{await f.navigate('loudness');reanalyze(f).dispatchEvent(new Event('click'));await settle();await editScope(f,scopes.find(s=>s.key==='profile'));assert.equal(f.get('loudness-run').disabled,true);f.click('loudness-run');await settle();assert.equal(f.confirms(),0);f.click('loudness-draft-resolve-profile');await settle();f.click('profile-settings-discard');await settle();await f.navigate('loudness');assert.equal(f.get('loudness-run').disabled,false);f.click('loudness-run');await settle();assert.equal(f.confirms(),1);assert.ok(!f.core.some(([method])=>method==='loudness.run'));}finally{f.restore();}
});
test('new preview receives focus and an accessible summary once, without automatic execution',async()=>{
  const f=await guardedFixture();try{await f.navigate('loudness');reanalyze(f).dispatchEvent(new Event('click'));await settle();const heading=f.get('loudness-preview-heading');assert.equal(document.activeElement,heading);assert.equal(heading.tabIndex,-1);assert.equal(heading.attrs['aria-describedby'],'loudness-preview-summary');assert.equal(f.get('loudness-preview-summary').attrs.role,'status');assert.equal(heading.focusCount,1);f.click('loudness-select-page');assert.equal(heading.focusCount,1);assert.equal(f.confirms(),0);}finally{f.restore();}
});
test('AI draft on Playlists immediately disables deletion with guidance; discard immediately restores it',async()=>{
  const f=await guardedFixture();try{await f.navigate('playlists');f.get('ai-panel').open=true;f.get('ai-panel').dispatchEvent(new Event('toggle'));await settle();const remove=f.get('offline-saved-delete-1');assert.equal(remove.disabled,false);f.get('optional-ai-enabled').checked=true;f.get('optional-ai-enabled').dispatchEvent(new Event('change'));assert.equal(f.dirty(),true);assert.equal(remove.disabled,true);assert.equal(f.get('offline-saved-draft-notice').hidden,false);assert.match(text(f.get('offline-saved-draft-notice')),/IA/);f.click('offline-saved-delete-1');assert.ok(!f.boundary.some(([kind])=>kind==='deletePlaylist'));f.click('optional-ai-discard');assert.equal(f.dirty(),false);assert.equal(remove.disabled,false);assert.equal(f.get('offline-saved-draft-notice').hidden,true);f.click('offline-saved-delete-1');await settle();assert.equal(f.boundary.filter(([kind])=>kind==='deletePlaylist').length,1);}finally{f.restore();}
});
test('clean Reanalizar is a preview; repeated click and native cancellation do not write',async()=>{
  const f=await guardedFixture();try{await f.navigate('loudness');assert.equal(f.dirty(),false);reanalyze(f).dispatchEvent(new Event('click'));reanalyze(f).dispatchEvent(new Event('click'));await settle();assert.equal(f.core.length,1);assert.deepEqual(f.core[0],['loudness.preview',{trackIds:[tracks[0].id],force:true}]);assert.equal(f.confirms(),0);f.click('loudness-run');await settle();assert.equal(f.confirms(),1);assert.ok(!f.core.some(([method])=>method==='loudness.run'));assert.match(f.get('loudness-result').textContent,/cancelada.*0 escrituras/);assert.equal(f.dirty(),false);}finally{f.restore();}
});

for(const scope of scopes.filter(s=>['profile','prep','ai'].includes(s.key))) test('explicit synthetic save recovers '+scope.name+' without clearing another draft',async()=>{
  const f=await guardedFixture();try{await editScope(f,scope);await f.navigate(scope.route);f.click(scope.save);await settle();assert.equal(f.dirty(),false);await f.navigate('loudness');reanalyze(f).dispatchEvent(new Event('click'));await settle();assert.equal(f.get('loudness-preview-section').hidden,false);assert.equal(f.core.length,1);assert.equal(f.confirms(),0);}finally{f.restore();}
});
test('combined profile and Prep drafts remain guarded until both are explicitly resolved',async()=>{
  const f=await guardedFixture();try{await editScope(f,scopes.find(s=>s.key==='profile'));await editScope(f,scopes.find(s=>s.key==='prep'));await f.navigate('preferences');f.click(scopes.find(s=>s.key==='profile').discard);await settle();assert.equal(f.dirty(),true);await f.navigate('loudness');reanalyze(f).dispatchEvent(new Event('click'));await settle();assert.equal(f.core.length,0);assert.equal(f.get('prep-genre').value,'Garage');await f.navigate('prep');f.click(scopes.find(s=>s.key==='prep').save);await settle();assert.equal(f.dirty(),false);await f.navigate('loudness');reanalyze(f).dispatchEvent(new Event('click'));await settle();assert.equal(f.core.length,1);}finally{f.restore();}
});
test('clean reloads, no-op inputs and edit-then-revert do not manufacture a stale global draft',async()=>{
  const f=await guardedFixture();try{
    for(const scope of scopes.filter(s=>s.key!=='editor')){if(scope.route==='editor'){await f.navigate('playlists');f.nodes().find(node=>node.tagName==='button'&&node.textContent==='Editar').dispatchEvent(new Event('click'));await settle();}await f.navigate(scope.route);const field=f.get(scope.id);const initial=typeof scope.value==='boolean'?field.checked:field.value;field.dispatchEvent(new Event(scope.event));await settle();assert.equal(f.dirty(),false,scope.name+' unchanged event');if(typeof scope.value==='boolean')field.checked=scope.value;else field.value=scope.value;field.dispatchEvent(new Event(scope.event));if(typeof scope.value==='boolean')field.checked=initial;else field.value=initial;field.dispatchEvent(new Event(scope.event));await settle();assert.equal(f.dirty(),false,scope.name+' reverted edit');}
    await f.navigate('loudness');f.click('loudness-refresh');await settle();reanalyze(f).dispatchEvent(new Event('click'));await settle();assert.equal(f.core.length,1);assert.equal(f.dirty(),false);
  }finally{f.restore();}
});
test('immediate discard then reanalysis uses clean synchronized state without losing remaining guards',async()=>{
  const f=await guardedFixture();try{await editScope(f,scopes.find(s=>s.key==='profile'));await f.navigate('preferences');f.click(scopes.find(s=>s.key==='profile').discard);await f.navigate('loudness');reanalyze(f).dispatchEvent(new Event('click'));await settle();assert.equal(f.core.length,1);assert.equal(f.dirty(),false);}finally{f.restore();}
});

test('a preview arriving after navigation never steals focus or exposes a stale run',async()=>{
  let finish;const wait=new Promise(resolve=>{finish=resolve;});const f=await guardedFixture(wait);try{await f.navigate('loudness');reanalyze(f).dispatchEvent(new Event('click'));await f.navigate('library');const focus=f.get('library-search');focus.focus();finish();await settle();assert.equal(document.activeElement,focus);assert.equal(f.get('loudness-preview-section').hidden,true);assert.equal(f.confirms(),0);}finally{f.restore();}
});
test('host fallback explains every possible draft scope without naming only editor/preferences',async()=>{
  const {userErrorMessage}=await import('../.out/renderer/errors.js');const message=userErrorMessage({code:'dirty_draft'});for(const scope of scopes)assert.match(message,scope.words);assert.match(message,/borradores se conservan/);
});

test('import explains the draft blocker and its resolve button stays available while import remains disabled',async()=>{
  const f=await guardedFixture();try{await editScope(f,scopes.find(s=>s.key==='prep'));await f.navigate('preferences');assert.equal(f.get('legacy-import-choose').disabled,true);assert.equal(f.get('legacy-import-draft-notice').hidden,false);assert.match(text(f.get('legacy-import-draft-notice')),/Controles de preparación/);assert.equal(f.get('legacy-import-draft-resolve-prep').disabled,false);f.click('legacy-import-choose');assert.ok(!f.boundary.some(([method])=>method==='previewLegacyImport'));f.click('legacy-import-draft-resolve-prep');await settle();assert.equal(document.activeElement,f.get('prep-genre'));assert.equal(f.get('prep-genre').value,'Garage');assert.equal(f.dirty(),true);f.click('prep-settings-discard');await settle();await f.navigate('preferences');assert.equal(f.get('legacy-import-choose').disabled,false);assert.equal(f.get('legacy-import-draft-notice').hidden,true);}finally{f.restore();}
});
