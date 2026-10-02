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
  classList = { toggle: (name, enabled) => { if (enabled) this.classes.add(name); else this.classes.delete(name); }, contains: (name) => this.classes.has(name) };
  setAttribute(name, value) { this.attrs[name] = value; }
  removeAttribute(name) { delete this.attrs[name]; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  closest() { return null; }
}
const tick = () => new Promise((resolve) => setImmediate(resolve));
const descendants = (element) => [element, ...element.children.flatMap(descendants)];
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
    assert.match(f.get('strategy-hint').textContent, /metadatos.*vibe|vibe.*metadatos/i);
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
  for (const name of ['strategy', 'minutes', 'role', 'genre', 'start', 'end', 'required', 'excluded']) { assert.match(html, new RegExp(`id="prep-${name}"`)); assert.match(html, new RegExp(`for="prep-${name}"`)); }
  assert.match(html, /<details[^>]*id="prep-advanced"/); assert.match(html, /id="prep-variants"/); assert.match(html, /no.*(?:inventa|fabrican|generan)/i);
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
    assert.deepEqual(f.get('prep-start').children.slice(1).map((option) => option.value), tracks.map((track) => track.id));
  } finally { f.restore(); }
});
test('current review enters Serato with its exact review identity and new generation invalidates export source', async () => {
 const previews=[]; const f=await fixture({chooseSeratoDestination:async()=>({destinationId:'dest',label:'_Serato_'}),previewSeratoExport:async input=>{previews.push(input);return {previewId:'p',sourceRevision:'r',filename:'Set.crate',destinationLabel:'_Serato_',trackCount:2,readiness:'ready',warnings:[],blockers:[],canCommit:true,tracks:tracks.slice(0,2),backup:{required:false}};}});
 const dynamic=id=>descendants(f.get('serato-container')).find(node=>node.id===id);
 try {
  await f.submit();f.get('export-review').dispatchEvent(new Event('click'));assert.equal(document.title,'XfinAudio · Exportar a Serato');
  dynamic('serato-export-choose').dispatchEvent(new Event('click'));await tick();dynamic('serato-export-preview').dispatchEvent(new Event('click'));await tick();
  assert.deepEqual(previews,[{source:{kind:'review',reviewId:'fresh'},destinationId:'dest',name:'Sesión equilibrada'}]);assert.equal(dynamic('serato-export-commit').disabled,false);
  f.variant('safe').dispatchEvent(new Event('click'));await tick();assert.equal(dynamic('serato-export-proposal').hidden,true);assert.equal(dynamic('serato-export-preview').disabled,true);
  f.get('export-review').dispatchEvent(new Event('click'));dynamic('serato-export-preview').dispatchEvent(new Event('click'));await tick();assert.equal(previews.at(-1).source.reviewId,'selected-review');
  await f.submit();assert.equal(dynamic('serato-export-proposal').hidden,true);assert.equal(dynamic('serato-export-preview').disabled,true);
 }finally{f.restore();}
});
