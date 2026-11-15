import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile } from 'node:fs/promises';
import * as model from '../renderer/model.ts';

const tracks = ['a', 'b', 'c'].map((letter, index) => ({ id: letter.repeat(64), title: letter, artist: 'Artist', bpm: 120 + index, key: '8A', energy: 5, duration: 180 }));
const strategies = [{ name: 'balanced', displayName: 'Equilibrada', description: 'Continuidad', requiresVibeMetadata: false }, { name: 'color', displayName: 'Color', description: 'Color existente', requiresVibeMetadata: true }];
const fields = { count: '2', name: '', strategy: '', minutes: '', role: '', genre: '', start: '', end: '', required: [], excluded: [] };
const planId = 'e80f5eca-8a03-4ed3-b832-c05e9be6566c';
const variants = ['safe', 'balanced', 'adventurous'].map((name) => ({ name, description: `${name} real`, trackCount: 2, readiness: 'ready', warnings: [], blockers: [], qualityScore: 0.8 }));
const review = (variant = 'balanced', id = 'fresh') => ({ reviewId: id, planId, variants, tracks: tracks.slice(0, 2), warnings: [], blockers: [], name: 'Sesión equilibrada', variant, readiness: 'ready' });

test('Prep request defaults retain the first-slice name and balanced request shape', () => {
  assert.deepEqual(model.buildPrepInput(fields, tracks, strategies), { targetTrackCount: 2, name: 'Sesión equilibrada' });
  assert.equal(model.buildPrepInput({ ...fields, name: '  Fiesta  ' }, tracks, strategies).name, 'Fiesta');
});
test('Prep validates real catalog, bounds and all known opaque track controls', () => {
  const input = model.buildPrepInput({ ...fields, count: '100', strategy: 'color', minutes: '600', role: 'peak_time', genre: '  House  ', start: tracks[0].id, end: tracks[1].id, required: [tracks[0].id], excluded: [tracks[2].id] }, tracks, strategies);
  assert.deepEqual(input, { targetTrackCount: 100, name: 'Sesión equilibrada', strategy: 'color', targetMinutes: 600, slotRole: 'peak_time', genreFocus: 'House', startTrackId: tracks[0].id, endTrackId: tracks[1].id, requiredTrackIds: [tracks[0].id], excludedTrackIds: [tracks[2].id] });
  assert.equal(model.buildPrepInput({ ...fields, minutes: '0.5' }, tracks, strategies).targetMinutes, 0.5);
  for (const patch of [{ count: '101' }, { minutes: '0' }, { minutes: '-1' }, { minutes: '601' }, { minutes: 'NaN' }, { minutes: 'Infinity' }, { strategy: 'unknown' }, { role: 'anything' }, { name: 'x'.repeat(201) }, { genre: 'x'.repeat(101) }, { start: '/tmp/music' }, { end: 'd'.repeat(64) }, { required: ['a'] }, { excluded: ['d'.repeat(64)] }]) assert.throws(() => model.buildPrepInput({ ...fields, ...patch }, tracks, strategies));
});
test('Prep rejects conflicting, duplicate and excessive requested tracks', () => {
  assert.equal(typeof model.buildPrepInput, 'function');
  for (const patch of [{ start: tracks[0].id, end: tracks[0].id }, { required: [tracks[0].id], excluded: [tracks[0].id] }, { start: tracks[0].id, excluded: [tracks[0].id] }, { end: tracks[0].id, excluded: [tracks[0].id] }, { required: [tracks[0].id, tracks[0].id] }, { required: tracks.map((track) => track.id) }, { start: tracks[0].id, end: tracks[1].id, required: [tracks[2].id] }]) assert.throws(() => model.buildPrepInput({ ...fields, ...patch }, tracks, strategies));
});
test('all real variants require a current, nonempty, unblocked, unsaved review before saving', () => {
  for (const variant of ['safe', 'balanced', 'adventurous']) {
    assert.equal(model.canSaveReview(review(variant)), true);
    for (const patch of [{ reviewId: '' }, { tracks: [] }, { readiness: 'blocked' }, { blockers: ['Missing'] }, { canSave: false }]) assert.equal(model.canSaveReview({ ...review(variant), ...patch }), false);
  }
  assert.equal(model.canSaveReview(review('saved')), false);
  assert.equal(model.canSaveReview(review('invented')), false);
});

class Element extends EventTarget {
  textContent = ''; value = ''; disabled = false; hidden = false; dataset = {}; children = []; attrs = {}; classes = new Set(); selectedOptions = [];
  get options() { return this.children; }
  classList = { toggle: (name, enabled) => { if (enabled) this.classes.add(name); else this.classes.delete(name); }, contains: (name) => this.classes.has(name) };
  setAttribute(name, value) { this.attrs[name] = value; }
  removeAttribute(name) { delete this.attrs[name]; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  closest() { return null; }
  focus() { document.activeElement=this; }
}
const lastForm = (patch = {}) => ({ targetTrackCount: null, targetMinutes: null, strategy: null, slotRole: null, name: null, startTrackId: null, endTrackId: null, ...patch });
const prepSettings = (patch = {}) => ({ revision: 'a'.repeat(64), requiredTrackIds: [], excludedTrackIds: [], genreFocus: '', unavailableRequiredCount: 0, unavailableExcludedCount: 0, lastForm: lastForm(), ...patch });
const tick = () => new Promise((resolve) => setImmediate(resolve));
const settle = async (count = 8) => { for (let index = 0; index < count; index++) await tick(); };
const descendants = (element) => [element, ...element.children.flatMap(descendants)];
const text = (node) => [node.textContent, ...node.children.map(text)].join(' ').replace(/\s+/g, ' ').trim();
const keydown = (node, key) => { const event = new Event('keydown', { cancelable: true }); event.key = key; node.dispatchEvent(event); return event; };
let sequence = 0;
async function fixture(overrides = {}) {
  const elements = new Map();
  const get = (id) => { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  const oldDocument = globalThis.document; const oldWindow = globalThis.window;
  get('prep-count').value = '2'; get('metadata-filter').value = 'all';
  const routeButton = new Element(); routeButton.dataset.route = 'library';
  let progress; const generated = []; const selected = []; const saved = [];
  const api = { listLibrary: async () => ({ tracks, count: tracks.length }), getPrepCatalog: async () => ({ strategies }), onProgress: (callback) => { progress = callback; return () => {}; }, generatePrep: async (input) => { generated.push(input); return review(); }, selectPrepVariant: async (input) => { selected.push(input); return review(input.variant, 'selected-review'); }, savePlaylist: async (input) => { saved.push(input); return { id: 'saved', name: input.name, trackCount: 2, createdAt: '' }; }, listPlaylists: async () => [], cancelCurrent: async () => {}, ...overrides };
  globalThis.document = { getElementById: get, createElement: () => new Element(), querySelectorAll: (selector) => selector === '[data-route]' ? [routeButton] : selector === '[data-mutation]' ? [...elements.values()].flatMap(descendants).filter((node) => 'mutation' in node.dataset) : [], title: '' };
  globalThis.window = Object.assign(new EventTarget(), { xfin: api });
  await import(`../.out/renderer/app.js?prepTest=${++sequence}`); await tick();
  return { get, generated, selected, saved, progress: (event) => progress(event), navigate: () => routeButton.dispatchEvent(new Event('click')), submit: async () => { get('prep-form').dispatchEvent(new Event('submit', { cancelable: true })); await tick(); }, variant: (name) => descendants(get('prep-variants')).find((node) => node.dataset.variant === name), restore: () => { globalThis.document = oldDocument; globalThis.window = oldWindow; } };
}
test('catalog loads independently of initial library and exposes prerequisite text', async () => {
  let resolveCatalog; const f = await fixture({ getPrepCatalog: () => new Promise((resolve) => { resolveCatalog = resolve; }) });
  try {
    assert.equal(f.get('library-total').textContent, '3');
    assert.equal(f.get('generate-prep').disabled, false);
    assert.equal(f.get('prep-strategy').disabled, true);
    resolveCatalog({ strategies }); await tick();
    assert.equal(f.get('prep-strategy').disabled, false);
    assert.equal(f.get('prep-strategy').children.length, 3);
    f.get('prep-strategy').value = 'color'; f.get('prep-strategy').dispatchEvent(new Event('change'));
    assert.match(f.get('strategy-hint').textContent, /metadatos de ambiente/);
    assert.equal(f.get('audio-player').children.length, 0);
  } finally { f.restore(); }
});
test('controller submits all controls, validates minutes and preserves optional default name', async () => {
  const f = await fixture();
  try {
    f.get('prep-minutes').value = '601'; await f.submit(); assert.equal(f.generated.length, 0);
    f.get('prep-minutes').value = '90'; f.get('prep-strategy').value = 'color'; f.get('prep-role').value = 'warmup'; f.get('prep-genre').value = 'House'; f.get('prep-start').value = tracks[0].id; f.get('prep-end').value = tracks[1].id; f.get('prep-required').selectedOptions = [{ value: tracks[0].id }]; f.get('prep-excluded').selectedOptions = [{ value: tracks[2].id }];
    await f.submit();
    assert.deepEqual(f.generated[0], { targetTrackCount: 2, name: 'Sesión equilibrada', strategy: 'color', targetMinutes: 90, slotRole: 'warmup', genreFocus: 'House', startTrackId: tracks[0].id, endTrackId: tracks[1].id, requiredTrackIds: [tracks[0].id], excludedTrackIds: [tracks[2].id] });
  } finally { f.restore(); }
});
test('variant selection reviews fresh tracks before explicit save and prevents repeated clicks', async () => {
  let resolveSelection; const selections = []; const f = await fixture({ selectPrepVariant: (input) => { selections.push(input); return new Promise((resolve) => { resolveSelection = resolve; }); } });
  try {
    await f.submit(); const button = f.variant('safe'); assert.ok(button); button.dispatchEvent(new Event('click')); button.dispatchEvent(new Event('click'));
    assert.equal(selections.length, 1); assert.deepEqual(selections[0], { planId, variant: 'safe' }); assert.equal(f.get('save-playlist').disabled, true);
    assert.equal(f.saved.length, 0); resolveSelection(review('safe', 'safe-review')); await tick();
    assert.equal(f.get('save-playlist').disabled, false); assert.match(f.get('review-variant').textContent, /SEGURA/);
    f.get('save-form').dispatchEvent(new Event('submit', { cancelable: true })); await tick();
    assert.deepEqual(f.saved, [{ name: 'Sesión equilibrada', reviewId: 'safe-review' }]); assert.equal(f.get('save-playlist').disabled, true);
  } finally { f.restore(); }
});
test('new generation invalidates old variant buttons and failed selection cannot save old review', async () => {
  let generation = 0; const f = await fixture({ generatePrep: async () => ({ ...review(), planId: `${++generation}` }), selectPrepVariant: async () => { throw new Error('[stale_plan] Stale plan'); } });
  try {
    await f.submit(); const oldButton = f.variant('safe'); await f.submit(); oldButton.dispatchEvent(new Event('click')); await tick(); assert.equal(f.get('save-playlist').disabled, false);
    f.variant('adventurous').dispatchEvent(new Event('click')); await tick(); assert.equal(f.get('save-playlist').disabled, true); assert.match(f.get('operation-detail').textContent, /alternativas.*vigentes/);
  } finally { f.restore(); }
});
test('cancel invalidates a pending variant result and cannot resurrect the review', async () => {
  let resolveSelection; const f = await fixture({ selectPrepVariant: () => new Promise((resolve) => { resolveSelection = resolve; }) });
  try {
    await f.submit(); f.variant('safe').dispatchEvent(new Event('click')); f.get('cancel-operation').dispatchEvent(new Event('click'));
    resolveSelection(review('safe')); await tick(); assert.equal(f.get('save-playlist').disabled, true); assert.equal(f.get('review-content').hidden, true); assert.equal(f.get('prep-variants').children.length, 0);
  } finally { f.restore(); }
});
test('navigation and core disconnect suppress late variant navigation and mutation', async () => {
  let resolveSelection; const f = await fixture({ selectPrepVariant: () => new Promise((resolve) => { resolveSelection = resolve; }) });
  try {
    await f.submit(); f.variant('safe').dispatchEvent(new Event('click')); f.navigate(); resolveSelection(review('safe')); await tick(); assert.equal(globalThis.document.title, 'XfinAudio · Biblioteca');
    f.variant('adventurous').dispatchEvent(new Event('click')); f.progress({ operation: 'core', phase: 'error', message: 'Stopped' }); resolveSelection(review('adventurous')); await tick(); assert.equal(f.get('save-playlist').disabled, true); assert.equal(f.get('prep-variants').children.length, 0); assert.equal(f.get('operation-label').textContent, 'Servicio local desconectado');
  } finally { f.restore(); }
});
test('Prep controls and variant comparison have Spanish accessible labels and an expandable advanced panel', async () => {
  const html = await readFile(new URL('../renderer/index.html', import.meta.url), 'utf8');
  for (const name of ['strategy', 'minutes', 'role']) { assert.match(html, new RegExp(`id="prep-${name}"`)); assert.match(html, new RegExp(`for="prep-${name}"`)); }
  // The free-text genre input became a list picker: the visible field is #prep-genre-search and
  // #prep-genre keeps carrying the value as genreFocus.
  assert.match(html, /id="prep-genre" type="hidden"/);
  assert.match(html, /<label for="prep-genre-search">Género preferido/);
  assert.match(html, /id="prep-genre-search"[^>]*role="combobox"/);
  assert.match(html, /id="prep-genre-search"[^>]*aria-controls="prep-genre-results"/);
  assert.match(html, /id="prep-genre-results"[^>]*role="listbox"/);
  assert.match(html, /id="prep-genre-clear"[^>]*>Quitar</);
  assert.match(html, /for="prep-start-search"/);
  assert.match(html, /id="prep-start-search"[^>]*role="combobox"/);
  assert.match(html, /id="prep-start-search"[^>]*aria-expanded="false"/);
  assert.match(html, /id="prep-start-search"[^>]*aria-controls="prep-start-results"/);
  assert.match(html, /id="prep-start-results"[^>]*role="listbox"/);
  assert.match(html, /id="prep-start-status"[^>]*aria-live="polite"/);
  assert.match(html, /id="prep-start-clear"[^>]*>Quitar</);
  assert.match(html, /id="prep-start" type="hidden"/);
  assert.doesNotMatch(html, /<select id="prep-start"/);
  // The closing, required and excluded picks use the same searchable picker: the visible label
  // names the search box while the existing select stays in the page as the hidden carrier.
  for (const name of ['end', 'required', 'excluded']) {
    assert.match(html, new RegExp(`<label for="prep-${name}-search">`));
    assert.match(html, new RegExp(`id="prep-${name}-search"[^>]*role="combobox"`));
    assert.match(html, new RegExp(`id="prep-${name}-search"[^>]*aria-expanded="false"`));
    assert.match(html, new RegExp(`id="prep-${name}-search"[^>]*aria-controls="prep-${name}-results"`));
    assert.match(html, new RegExp(`id="prep-${name}-results"[^>]*role="listbox"[^>]*hidden`));
    assert.match(html, new RegExp(`id="prep-${name}-status"[^>]*aria-live="polite"`));
    assert.match(html, new RegExp(`id="prep-${name}-chips"[^>]*class="track-chips"`));
    assert.match(html, new RegExp(`<select id="prep-${name}"[^>]*hidden`), 'the select stays mounted as the value carrier');
    assert.match(html, new RegExp(`id="prep-${name}"[^>]*(multiple )?hidden`));
  }
  assert.match(html, /<select id="prep-end" hidden[^>]*><option value="">Sin preferencia<\/option><\/select>/);
  assert.match(html, /<select id="prep-required" multiple hidden/);
  assert.match(html, /<select id="prep-excluded" multiple hidden/);
  assert.match(html, /<details[^>]*id="prep-advanced"/); assert.match(html, /id="prep-variants"/); assert.match(html, /no.*(?:inventa|fabrican|generan)/i);
});

test('a catalog strategy with a known stable name shows its Spanish name and description, and keeps its name as the submitted value', async () => {
  const known = [{ name: 'chill', displayName: 'Chill', description: 'Prefer lower energy and lower BPM selections.', requiresVibeMetadata: false }];
  const f = await fixture({ getPrepCatalog: async () => ({ strategies: known }) });
  try {
    const option = f.get('prep-strategy').children[1];
    assert.equal(option.textContent, 'Relax'); assert.equal(option.value, 'chill');
    assert.match(f.get('strategy-hint').textContent, /predeterminada/i);
    f.get('prep-strategy').value = 'chill'; f.get('prep-strategy').dispatchEvent(new Event('change'));
    assert.equal(f.get('strategy-hint').textContent, 'Prefiere pistas de energía y BPM más bajos.');
    await f.submit(); assert.equal(f.generated[0].strategy, 'chill');
  } finally { f.restore(); }
});
test('catalog failure remains local, retries successfully, and cannot hide a core disconnect', async () => {
  let calls = 0; let resolveCatalog; const f = await fixture({ getPrepCatalog: () => ++calls === 1 ? Promise.reject(new Error('Unavailable')) : new Promise((resolve) => { resolveCatalog = resolve; }) });
  try {
    assert.equal(f.get('catalog-retry').hidden, false); assert.equal(f.get('generate-prep').disabled, false); assert.match(f.get('strategy-hint').textContent, /predeterminada/);
    f.get('catalog-retry').dispatchEvent(new Event('click')); resolveCatalog({ strategies }); await tick(); assert.equal(f.get('prep-strategy').children.length, 3);
    f.get('catalog-retry').dispatchEvent(new Event('click')); f.progress({ operation: 'core', phase: 'error', message: 'Offline' }); resolveCatalog({ strategies }); await tick(); assert.equal(f.get('prep-strategy').disabled, true); assert.equal(f.get('operation-detail').textContent, 'El servicio local dejó de responder. Reinicia XfinAudio para volver a conectar.');
  } finally { f.restore(); }
});
test('new scan invalidates the plan even when folder selection is dismissed', async () => {
  const f = await fixture({ chooseLibrary: async () => null });
  try {
    await f.submit(); const oldButton = f.variant('safe'); f.get('choose-library').dispatchEvent(new Event('click')); await tick(); oldButton.dispatchEvent(new Event('click')); await tick();
    assert.equal(f.selected.length, 0); assert.equal(f.get('save-playlist').disabled, true); assert.equal(f.get('prep-variants').children.length, 0);
  } finally { f.restore(); }
});
test('blocked alternatives remain reviewable while saving is disabled and warnings are visible', async () => {
  const f = await fixture({ selectPrepVariant: async () => ({ ...review('adventurous'), readiness: 'blocked', warnings: ['Falta información vibe'], blockers: ['Pistas insuficientes'] }) });
  try {
    await f.submit(); f.variant('adventurous').dispatchEvent(new Event('click')); await tick();
    assert.equal(f.get('review-content').hidden, false); assert.equal(f.get('review-readiness').textContent, 'Necesita atención'); assert.equal(f.get('save-playlist').disabled, true);
    const notices = descendants(f.get('review-alerts')).map((node) => node.textContent).join(' '); assert.match(notices, /Falta información vibe/); assert.match(notices, /Pistas insuficientes/);
    assert.deepEqual(f.get('prep-end').children.slice(1).map((option) => option.value), tracks.map((track) => track.id), 'the closing select still lists every track');
  } finally { f.restore(); }
});
test('current review enters Serato with its exact review identity and new generation invalidates export source', async () => {
 const previews=[]; const f=await fixture({chooseSeratoDestination:async()=>({destinationId:'dest',label:'_Serato_'}),previewSeratoExport:async input=>{previews.push(input);return {previewId:'p',sourceRevision:'r',filename:'Set.crate',destinationLabel:'_Serato_',trackCount:2,readiness:'ready',warnings:[],blockers:[],canCommit:true,tracks:tracks.slice(0,2),backup:{required:false}};}});
 const dynamic=id=>descendants(f.get('serato-container')).find(node=>node.id===id);
 try {
  await f.submit();f.get('export-review').dispatchEvent(new Event('click'));assert.equal(document.title,'XfinAudio · Exportar a Serato');
  dynamic('serato-export-choose').dispatchEvent(new Event('click'));await tick();dynamic('serato-export-preview').dispatchEvent(new Event('click'));await tick();
  assert.deepEqual(previews,[{source:{kind:'review',reviewId:'fresh'},destinationId:'dest'}]);assert.equal(dynamic('serato-export-commit').disabled,false);
  f.variant('safe').dispatchEvent(new Event('click'));await tick();assert.equal(dynamic('serato-export-proposal').hidden,true);assert.equal(dynamic('serato-export-preview').disabled,true);
  f.get('export-review').dispatchEvent(new Event('click'));dynamic('serato-export-preview').dispatchEvent(new Event('click'));await tick();assert.equal(previews.at(-1).source.reviewId,'selected-review');
  await f.submit();assert.equal(dynamic('serato-export-proposal').hidden,true);assert.equal(dynamic('serato-export-preview').disabled,true);
 }finally{f.restore();}
});
for(const scope of ['required','excluded','both'])test(`101 distinct ${scope} controls reveal the offending list before any generate call`,async()=>{
 const many=Array.from({length:101},(_,index)=>({...tracks[0],id:index.toString(16).padStart(64,'0')}));const f=await fixture({listLibrary:async()=>({tracks:many,count:many.length})});try{
  f.get('prep-count').value='100';const group=f.get('prep-track-options');group.tagName='DETAILS';group.open=false;
  for(const field of ['required','excluded']){const input=f.get('prep-'+field);input.selectedOptions=scope===field||scope==='both'?many.map(track=>({value:track.id})):[];f.get('prep-'+field+'-search').parentElement=group;}
  await f.submit();assert.equal(f.generated.length,0);assert.equal(document.activeElement,f.get(scope==='excluded'?'prep-excluded-search':'prep-required-search'),'the visible search box of the offending picker takes the focus');assert.equal(group.open,true);assert.match(f.get('prep-validation').textContent,/100 pistas distintas/);
 }finally{f.restore();}
});
test('a large library keeps the opening search usable without building one option per track',async()=>{
 const many=Array.from({length:650},(_,i)=>({...tracks[0],id:i.toString(16).padStart(64,'0'),title:'Track '+i}));const f=await fixture({listLibrary:async()=>({tracks:many,count:many.length})});try{
  assert.equal(f.get('library-total').textContent,'650');assert.equal(f.get('prep-start-results').children.length,0,'no per-track DOM is built before the search is used');
  f.get('prep-required').selectedOptions=[{value:many[5].id}];await f.submit();
  assert.equal(f.get('prep-end').children.length,many.length+1,'no track is silently truncated from the closing select');
  const search=f.get('prep-start-search');search.value='Track 649';search.dispatchEvent(new Event('input'));
  assert.equal(f.get('prep-start-results').children.length,1,'the opening search reaches every track without rendering every option');
  assert.match(text(f.get('prep-start-results').children[0]),/Track 649 Artist 120 BPM · 8A/);
  assert.equal(f.get('prep-required').children.length,many.length,'no track is silently truncated from the multi-select');
  assert.equal(f.get('prep-required').children.find(option=>option.value===many[5].id).selected,true,'deferred population preserves the selected ID');
 }finally{f.restore();}
});
test('the known count-shortfall warning is Spanish with exact counts and unknown warnings remain intact',async()=>{
 const f=await fixture({generatePrep:async()=>({...review(),warnings:['Track count shortfall: selected 8 of 20 requested tracks','Unknown actionable warning: check this source']})});try{
  await f.submit();const warnings=descendants(f.get('review-alerts')).map(node=>node.textContent).join(' ');assert.match(warnings,/Se seleccionaron 8 de las 20 pistas solicitadas/);assert.match(warnings,/Unknown actionable warning: check this source/);assert.doesNotMatch(warnings,/Track count shortfall/);
 }finally{f.restore();}
});
test('opening track is chosen with a searchable combobox and sent as startTrackId', async () => {
  const f = await fixture();
  try {
    const search = f.get('prep-start-search'); const list = f.get('prep-start-results');
    assert.equal(list.hidden, true); assert.equal(f.get('prep-start').value, '');
    search.value = 'ARTIST'; search.dispatchEvent(new Event('input'));
    assert.equal(list.hidden, false); assert.equal(search.attrs['aria-expanded'], 'true');
    assert.equal(list.children.length, 3, 'matching tracks appear while typing');
    assert.deepEqual(list.children.map((item) => item.attrs.role), ['option', 'option', 'option']);
    assert.match(text(list.children[0]), /a Artist 120 BPM · 8A/);
    assert.equal(search.attrs['aria-activedescendant'], 'prep-start-option-0');
    assert.equal(list.children[0].attrs['aria-selected'], 'true');
    assert.equal(f.get('prep-start-status').textContent, '3 coincidencias. Usa las flechas para moverte y Enter para elegir.');
    keydown(search, 'ArrowDown');
    assert.equal(search.attrs['aria-activedescendant'], 'prep-start-option-1');
    assert.equal(list.children[1].attrs['aria-selected'], 'true');
    keydown(search, 'ArrowUp'); keydown(search, 'ArrowUp');
    assert.equal(search.attrs['aria-activedescendant'], 'prep-start-option-2', 'arrows wrap around the options');
    keydown(search, 'ArrowDown'); keydown(search, 'ArrowDown'); keydown(search, 'Enter');
    assert.equal(f.get('prep-start').value, tracks[1].id);
    assert.equal(search.value, ''); assert.equal(list.hidden, true); assert.equal(search.attrs['aria-expanded'], 'false');
    assert.equal(f.get('prep-start-selected-label').textContent, 'b · Artist');
    assert.equal(f.get('prep-start-clear').hidden, false);
    assert.equal(f.get('prep-start-selected-meta').textContent, '121 BPM · 8A');
    assert.equal(f.get('prep-start-status').textContent, 'Pista de apertura: b · Artist.');
    await f.submit();
    assert.equal(f.generated[0].startTrackId, tracks[1].id);
  } finally { f.restore(); }
});
test('opening search closes with Escape, selects by click and Quitar keeps the request shape', async () => {
  const f = await fixture();
  try {
    const search = f.get('prep-start-search'); const list = f.get('prep-start-results');
    search.value = 'b'; search.dispatchEvent(new Event('input'));
    assert.equal(list.children.length, 1);
    assert.equal(keydown(search, 'Escape').defaultPrevented, true);
    assert.equal(list.hidden, true); assert.equal(search.attrs['aria-expanded'], 'false');
    assert.equal(f.get('prep-start').value, '', 'Escape never changes the stored choice');
    search.dispatchEvent(new Event('input'));
    list.children[0].dispatchEvent(new Event('click'));
    assert.equal(f.get('prep-start').value, tracks[1].id);
    assert.equal(f.get('prep-start-selected-label').textContent, 'b · Artist');
    f.get('prep-start-clear').dispatchEvent(new Event('click'));
    assert.equal(f.get('prep-start').value, '');
    assert.equal(f.get('prep-start-selected-label').textContent, 'Sin preferencia');
    assert.equal(f.get('prep-start-clear').hidden, true);
    assert.equal(f.get('prep-start-status').textContent, 'Sin preferencia de apertura.');
    await f.submit();
    assert.equal('startTrackId' in f.generated[0], false, 'no choice sends no opening track');
  } finally { f.restore(); }
});
test('an opening id that is no longer in the library stays visible and blocks generation', async () => {
  const f = await fixture();
  try {
    f.get('prep-start').value = 'f'.repeat(64);
    await f.submit();
    assert.equal(f.generated.length, 0);
    assert.equal(f.get('prep-start-selection').hidden, false);
    assert.equal(f.get('prep-start-selected-label').textContent, 'No disponible: ffffffff');
    assert.equal(f.get('prep-start-selection').attrs['data-state'], 'unavailable');
    assert.match(f.get('prep-validation').textContent, /biblioteca actual/);
    assert.equal(document.activeElement, f.get('prep-start-search'));
  } finally { f.restore(); }
});
test('the opening and closing tracks still cannot be the same track', async () => {
  const f = await fixture();
  try {
    const search = f.get('prep-start-search');
    search.value = 'artist'; search.dispatchEvent(new Event('input')); keydown(search, 'Enter');
    assert.equal(f.get('prep-start').value, tracks[0].id);
    f.get('prep-end').value = tracks[0].id;
    await f.submit();
    assert.equal(f.generated.length, 0);
    assert.match(f.get('prep-validation').textContent, /La apertura y el cierre deben ser pistas distintas/);
  } finally { f.restore(); }
});
test('the last generated form is shown again on the next start and reaches the next request', async () => {
  const remembered = lastForm({ targetTrackCount: 12, targetMinutes: 90, strategy: 'color', slotRole: 'warmup', name: 'Viernes', startTrackId: tracks[0].id, endTrackId: tracks[1].id });
  const f = await fixture({ prepSettings: async () => prepSettings({ lastForm: remembered }), savePrepSettings: async (input) => prepSettings({ ...input, revision: 'b'.repeat(64) }) });
  try {
    await settle();
    assert.equal(f.get('prep-name').value, 'Viernes');
    assert.equal(f.get('prep-count').value, '12');
    assert.equal(f.get('prep-minutes').value, '90');
    assert.equal(f.get('prep-role').value, 'warmup');
    assert.equal(f.get('prep-strategy').value, 'color');
    assert.equal(f.get('prep-start').value, tracks[0].id);
    assert.equal(f.get('prep-start-selected-label').textContent, 'a · Artist');
    assert.equal(f.get('prep-end').value, tracks[1].id);
    await f.submit();
    assert.deepEqual(f.generated[0], { targetTrackCount: 12, name: 'Viernes', strategy: 'color', targetMinutes: 90, slotRole: 'warmup', startTrackId: tracks[0].id, endTrackId: tracks[1].id });
  } finally { f.restore(); }
});
test('a remembered track that left the library stays visible as unavailable and blocks generation', async () => {
  const goneStart = 'f'.repeat(64), goneEnd = 'e'.repeat(64);
  const f = await fixture({ prepSettings: async () => prepSettings({ lastForm: lastForm({ startTrackId: goneStart, endTrackId: goneEnd }) }), savePrepSettings: async (input) => prepSettings({ ...input, revision: 'b'.repeat(64) }) });
  try {
    await settle();
    assert.equal(f.get('prep-start').value, goneStart);
    assert.equal(f.get('prep-start-selected-label').textContent, 'No disponible: ffffffff');
    assert.equal(f.get('prep-start-selection').attrs['data-state'], 'unavailable');
    assert.equal(f.get('prep-end').value, goneEnd);
    const missing = f.get('prep-end').children.find((option) => option.value === goneEnd);
    assert.ok(missing, 'the closing select keeps the remembered identity instead of dropping it');
    assert.equal(missing.disabled, true);
    assert.equal(missing.selected, true);
    assert.match(missing.textContent, /No disponible/);
    assert.equal(f.get('prep-end-chips').children.length, 1);
    assert.equal(f.get('prep-end-chips').children[0].attrs['data-state'], 'unavailable');
    assert.match(text(f.get('prep-end-chips')), /No disponible: eeeeeeee/);
    await f.submit();
    assert.equal(f.generated.length, 0, 'an unavailable remembered track is never silently dropped');
    assert.match(f.get('prep-validation').textContent, /biblioteca actual/);
  } finally { f.restore(); }
});
test('a form value the user already changed is not replaced by the remembered form after a library refresh', async () => {
  const f = await fixture({
    prepSettings: async () => prepSettings({ lastForm: lastForm({ targetTrackCount: 12, name: 'Viernes' }) }),
    savePrepSettings: async (input) => prepSettings({ ...input, revision: 'b'.repeat(64) }),
    rescanLibrary: async () => ({ tracks, count: tracks.length }),
  });
  try {
    await settle();
    assert.equal(f.get('prep-count').value, '12');
    f.get('prep-count').value = '25';
    f.get('prep-count').dispatchEvent(new Event('input'));
    f.get('library-status-rescan').dispatchEvent(new Event('click'));
    await settle(20);
    assert.equal(f.get('prep-count').value, '25');
    assert.equal(f.get('prep-name').value, 'Viernes');
  } finally { f.restore(); }
});
test('the closing track is chosen with a search picker that keeps #prep-end as the value carrier', async () => {
  const f = await fixture();
  try {
    const search = f.get('prep-end-search'); const list = f.get('prep-end-results'); const chips = f.get('prep-end-chips');
    assert.equal(list.hidden, true); assert.equal(text(chips), 'Sin preferencia');
    search.value = 'ARTIST'; search.dispatchEvent(new Event('input'));
    assert.equal(list.hidden, false); assert.equal(search.attrs['aria-expanded'], 'true');
    assert.equal(list.children.length, 3, 'matching tracks appear while typing');
    assert.match(text(list.children[0]), /a Artist 120 BPM · 8A/);
    assert.equal(search.attrs['aria-activedescendant'], 'prep-end-option-0');
    assert.equal(list.children[0].attrs['aria-selected'], 'true');
    assert.equal(f.get('prep-end-status').textContent, '3 coincidencias. Usa las flechas para moverte y Enter para elegir.');
    keydown(search, 'ArrowDown');
    assert.equal(search.attrs['aria-activedescendant'], 'prep-end-option-1');
    keydown(search, 'Enter');
    assert.equal(f.get('prep-end').value, tracks[1].id, 'the hidden select holds the chosen id');
    assert.equal(list.hidden, true); assert.equal(search.value, ''); assert.equal(search.attrs['aria-expanded'], 'false');
    assert.equal(chips.children.length, 1);
    assert.match(text(chips), /b · Artist 121 BPM · 8A Quitar/);
    assert.equal(f.get('prep-end-status').textContent, 'Pista de cierre: b · Artist.');
    await f.submit();
    assert.equal(f.generated[0].endTrackId, tracks[1].id);
  } finally { f.restore(); }
});
test('the closing picker holds one track and Quitar clears it without leaving a value', async () => {
  const f = await fixture();
  try {
    const search = f.get('prep-end-search'); const chips = f.get('prep-end-chips');
    const pick = (query) => { search.value = query; search.dispatchEvent(new Event('input')); return f.get('prep-end-results').children[0]; };
    pick('b').dispatchEvent(new Event('click'));
    assert.equal(f.get('prep-end').value, tracks[1].id);
    pick('c').dispatchEvent(new Event('click'));
    assert.equal(f.get('prep-end').value, tracks[2].id, 'a second choice replaces the first');
    assert.equal(chips.children.length, 1, 'the closing picker never holds two tracks');
    assert.match(text(chips), /c · Artist/);
    const remove = descendants(chips.children[0]).find((node) => node.textContent === 'Quitar');
    assert.ok(remove, 'each chosen track is removed with «Quitar»');
    remove.dispatchEvent(new Event('click'));
    assert.equal(f.get('prep-end').value, '', 'Quitar leaves no closing track in the carrier');
    assert.equal(text(chips), 'Sin preferencia');
    assert.equal(f.get('prep-end-status').textContent, 'Sin preferencia de cierre.');
    await f.submit();
    assert.equal('endTrackId' in f.generated[0], false);
  } finally { f.restore(); }
});
test('required and excluded pickers hold several tracks and reach the request in the chosen order', async () => {
  const f = await fixture();
  try {
    const pick = (id, query) => { const search = f.get(`prep-${id}-search`); search.value = query; search.dispatchEvent(new Event('input')); f.get(`prep-${id}-results`).children[0].dispatchEvent(new Event('click')); };
    pick('required', 'c'); pick('required', 'a');
    assert.equal(f.get('prep-required-chips').children.length, 2);
    assert.match(text(f.get('prep-required-chips').children[0]), /c · Artist 122 BPM · 8A Quitar/);
    assert.equal(f.get('prep-required-status').textContent, 'Pista obligatoria: a · Artist.');
    pick('excluded', 'b');
    assert.equal(f.get('prep-excluded-status').textContent, 'Pista excluida: b · Artist.');
    assert.match(text(f.get('prep-excluded-chips')), /b · Artist/);
    const remove = descendants(f.get('prep-required-chips').children[0]).find((node) => node.textContent === 'Quitar');
    remove.dispatchEvent(new Event('click'));
    assert.equal(f.get('prep-required-chips').children.length, 1);
    assert.equal(f.get('prep-required-status').textContent, 'Quitada: c · Artist.');
    await f.submit();
    assert.deepEqual(f.generated[0].requiredTrackIds, [tracks[0].id]);
    assert.deepEqual(f.generated[0].excludedTrackIds, [tracks[1].id]);
  } finally { f.restore(); }
});
test('saved required, excluded and closing choices still ride the same selects and now show as chips', async () => {
  const f = await fixture({ prepSettings: async () => prepSettings({ requiredTrackIds: [tracks[0].id], excludedTrackIds: [tracks[1].id], lastForm: lastForm({ endTrackId: tracks[2].id }) }), savePrepSettings: async (input) => prepSettings({ ...input, revision: 'b'.repeat(64) }) });
  try {
    await settle();
    assert.match(text(f.get('prep-required-chips')), /a · Artist/);
    assert.match(text(f.get('prep-excluded-chips')), /b · Artist/);
    assert.match(text(f.get('prep-end-chips')), /c · Artist/);
    await f.submit();
    assert.deepEqual(f.generated[0].requiredTrackIds, [tracks[0].id]);
    assert.deepEqual(f.generated[0].excludedTrackIds, [tracks[1].id]);
    assert.equal(f.generated[0].endTrackId, tracks[2].id);
  } finally { f.restore(); }
});
