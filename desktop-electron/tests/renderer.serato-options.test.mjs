/**
 * S2 in the real app: «Opciones de exportación» opens the export screen directly — from the
 * review screen next to «Exportar a Serato» and from every saved playlist card — carrying the
 * same source and name the quick export would use, and obeying the same gating. The quick
 * export itself keeps exporting in one click from both places.
 */
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import test from 'node:test';
const { validateRequest } = createRequire(import.meta.url)('../.out/main/security.js');
class Element extends EventTarget {
  constructor(tag = 'div') { super(); this.tagName = tag; }
  get options() { return this.children.filter(node => node.tagName === 'option'); }
  get selectedOptions() { return this.options.filter(node => node.selected); }
  textContent = ''; value = ''; checked = false; disabled = false; hidden = false; dataset = {}; children = []; attrs = {}; classes = new Set(); className = ''; id = ''; parent = null; paused = true; duration = 0; currentTime = 0;
  classList = { toggle: (key, active) => active ? this.classes.add(key) : this.classes.delete(key), contains: (key) => this.classes.has(key) };
  setAttribute(key, value) { this.attrs[key] = String(value); } removeAttribute(key) { delete this.attrs[key]; }
  append(...nodes) { for (const node of nodes) node.parent = this; this.children.push(...nodes); }
  replaceChildren(...nodes) { for (const node of nodes) node.parent = this; this.children = nodes; }
  closest() { return null; } focus() {} pause() { this.paused = true; } load() {} async play() { this.paused = false; }
}
const all = (node) => [node, ...node.children.flatMap(all)];
const text = (node) => [node.textContent, ...node.children.map(text)].join(' ');
const tick = () => new Promise((resolve) => setImmediate(resolve));
const settle = async () => { for (let i = 0; i < 5; i++) await tick(); };
const prefs = (patch = {}) => ({ revision: 'a'.repeat(64), previewVolume: .25, watchLibrary: true, recoveryWarning: false, libraryLabels: ['DJ'], capabilities: { loudnessWriteback: false, providers: false, language: 'es' }, ...patch });
const status = (patch = {}) => ({ revision: 1, changeState: 'restored', watchState: 'active', rootCount: 1, watchedCount: 1, ...patch });
const tracks = ['a', 'b'].map((id) => ({ id: id.repeat(64), title: id, artist: 'DJ', bpm: 120, key: '8A', energy: 5, duration: 120, missing: false }));
const profileStatus = (patch = {}) => { const value = { state: 'complete', totalTracks: 2, readyCount: 2, spectralReadyCount: 2, danceabilityReadyCount: 2, edgeReadyCount: 2, pendingCount: 0, failedCount: 0, estimatedRemainingSeconds: null, ...patch }; return { ...value, spectralPendingCount: value.totalTracks - value.spectralReadyCount, danceabilityPendingCount: value.totalTracks - value.danceabilityReadyCount, edgePendingCount: value.totalTracks - value.edgeReadyCount }; };
const completion = (patch = {}) => ({ cancelled: false, tracks, status: profileStatus(), completeCount: 2, incompleteCount: 0, ...patch });
const detailed = (patch = {}) => ({ reviewId: 'review', name: 'Set', variant: 'balanced', readiness: 'ready', tracks, warnings: [], blockers: [], qualityScore: .8, engineFacts: 'Local engine: 2 tracks', readinessSummary: 'Ready', readinessChecks: [{ label: 'Metadata', status: 'ready', detail: 'Complete' }], transitions: [{ index: 1, leftTrackId: tracks[0].id, rightTrackId: tracks[1].id, totalScore: .8, compatibilityScore: .9, mixabilityScore: .7, components: { bpm: 1, key: .8 }, explanations: ['Compatible'], warnings: [] }], protectedTrackIds: [], ...patch });
const savedId = '12345678-1234-4123-8123-123456789012';
const saved = { id: '1', name: 'Guardada', trackCount: 2, createdAt: '' };
const savedReview = (patch = {}) => detailed({ reviewId: savedId, name: 'Guardada', variant: 'saved', savedPlaylistId: '1', ...patch });
const OTHER_SOURCE = 'Elige una selección revisada, una lista de metadatos o una playlist guardada para exportar.';
let sequence = 0;
async function fixture(overrides = {}) {
  const previousDocument = globalThis.document; const previousWindow = globalThis.window; const elements = new Map(); const calls = []; const exported = [];
  const nodes = () => [...elements.values()].flatMap(all);
  const get = (id) => { const dynamic = nodes().find((node) => node.id === id); if (dynamic) return dynamic; if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  const routes = ['library', 'prep', 'preferences', 'playlists', 'editor', 'review', 'live', 'serato'].map((route) => { const button = new Element('button'); button.dataset.route = route; return button; });
  const api = {
    listLibrary: async () => ({ tracks, count: 2 }), getPrepCatalog: async () => ({ strategies: [] }), onProgress: () => () => {},
    getPreferences: async () => prefs(), savePreferences: async (input) => ({ ...prefs(), ...input, revision: 'b'.repeat(64) }),
    getLibraryStatus: async () => status(), onLibraryStatus: () => () => {},
    getProfileStatus: async () => profileStatus(), getProfileSettings: async () => ({ revision: 'a'.repeat(64), spectralCohesion: .5 }), saveProfileSettings: async (input) => ({ ...input, revision: 'b'.repeat(64) }), completeProfiles: async () => completion(),
    rescanLibrary: async () => ({ tracks, count: 2 }), setDraftDirty: async () => {},
    listPlaylists: async () => [saved],
    openPlaylistEditor: async () => ({ id: '1', editId: 'edit', revision: 'r1', name: 'Guardada', tracks, missingTrackCount: 0 }), discardPlaylistEdit: async () => ({ id: '1', editId: 'edit', revision: 'r1', name: 'Guardada', tracks, missingTrackCount: 0 }),
    generatePrep: async (input) => { calls.push(['generate', input]); return detailed(); },
    openPlaylist: async (input) => { calls.push(['open', input]); return savedReview(); },
    detectSeratoDestination: async () => { calls.push(['detect']); return { destinationId: 'dest', label: '_Serato_ · dd' }; },
    quickSeratoExport: async (input) => { exported.push(validateRequest('quickSeratoExport', input)); return { status: 'cancelled' }; },
    ...overrides,
  };
  globalThis.document = {
    getElementById: get, createElement: (tag) => new Element(tag), title: '',
    querySelectorAll: (selector) => {
      if (selector === '[data-route]' || selector === '.nav-item') return routes;
      if (selector === '[data-mutation]') return nodes().filter((node) => node.dataset && 'mutation' in node.dataset);
      return [];
    },
  };
  globalThis.window = Object.assign(new EventTarget(), { xfin: api }); get('metadata-filter').value = 'all'; get('prep-count').value = '2';
  await import(`../.out/renderer/app.js?seratoOptions=${++sequence}`); await settle();
  const find = (caption) => nodes().find((node) => node.tagName === 'button' && node.textContent === caption);
  // The quick notice offers its own «Opciones de exportación»; the card one lives in its actions row.
  const cardOptions = () => nodes().find((node) => node.tagName === 'button' && node.textContent === 'Opciones de exportación' && node.parent?.className === 'playlist-actions');
  const click = (id) => get(id).dispatchEvent(new Event('click'));
  const navigate = async (route) => { routes.find((button) => button.dataset.route === route).dispatchEvent(new Event('click')); await settle(); };
  return {
    get, calls, nodes, find, cardOptions, click, navigate, exported,
    generated: () => { get('prep-form').dispatchEvent(new Event('submit', { cancelable: true })); },
    openSaved: async () => { await navigate('playlists'); find('Abrir playlist →').dispatchEvent(new Event('click')); await settle(); },
    restore: () => { window.dispatchEvent(new Event('beforeunload')); globalThis.document = previousDocument; globalThis.window = previousWindow; },
  };
}
test('the review screen opens «Opciones de exportación» without starting an export (S2)', async () => {
  const f = await fixture();
  try {
    const html = await readFile(new URL('../renderer/index.html', import.meta.url), 'utf8');
    assert.match(html, /<button id="export-review-options" type="button" class="button subtle">Opciones de exportación<\/button>/, 'the button is a secondary-styled, Spanish-labelled button');
    assert.match(html, /id="export-review"[\s\S]{0,200}?id="export-review-options"/, 'it sits next to «Exportar a Serato» on the review screen');
    await f.navigate('prep'); f.generated(); await settle();
    const options = f.get('export-review-options');
    assert.equal(options.disabled, false, 'a review that can export can open its options');
    f.click('export-review-options'); await settle();
    assert.equal(f.get('page-title').textContent, 'Exportar a Serato', 'the click reaches the export options screen');
    assert.equal(f.get('serato-export-source').textContent, 'Origen: selección revisada actual', 'the options screen received the review source');
    assert.equal(f.get('serato-export-name').value, '', 'a generated list keeps the automatic name the quick export would use');
    assert.deepEqual(f.calls.filter(([kind]) => kind === 'detect'), [['detect']], 'the options screen ran its own destination detection');
    assert.deepEqual(f.exported, [], 'opening the options screen never starts an export');
  } finally { f.restore(); }
});
test('a saved playlist card opens «Opciones de exportación» with its own source and name (S2)', async () => {
  const f = await fixture();
  try {
    await f.navigate('playlists'); await settle();
    const options = f.cardOptions();
    assert.ok(options, 'each saved card carries the options button');
    const quickExport = f.find('Exportar a Serato');
    assert.equal(options.parent, quickExport.parent, 'both live in the card actions row');
    assert.equal(options.parent.children.indexOf(options), options.parent.children.indexOf(quickExport) + 1, 'the options button sits next to «Exportar a Serato»');
    assert.equal(options.className, 'button subtle', 'the options button is secondary-styled');
    assert.equal(options.attrs['aria-label'], 'Opciones de exportación: Guardada', 'it names the playlist it belongs to');
    assert.equal(options.disabled, false);
    options.dispatchEvent(new Event('click')); await settle();
    assert.equal(f.get('page-title').textContent, 'Exportar a Serato', 'the click reaches the export options screen');
    assert.equal(f.get('serato-export-source').textContent, 'Origen: playlist guardada completa. Los cambios sin guardar del editor no se incluyen.');
    assert.equal(f.get('serato-export-name').value, 'Guardada', 'the saved name travels, exactly as the quick export would send it');
    assert.deepEqual(f.exported, [], 'opening the options screen never starts an export');
  } finally { f.restore(); }
});
test('both entry points reach the same export screen, whose «Pistas por tramo» follows «Dividir en tramos» (S1)', async () => {
  const f = await fixture();
  const control = (suffix) => all(f.get('serato-container')).find((node) => node.id === `serato-export-${suffix}`);
  try {
    // The review screen and the saved-playlist card both open createSeratoExportView (app.ts), so one screen serves both.
    await f.navigate('prep'); f.generated(); await settle();
    f.click('export-review-options'); await settle();
    assert.ok(control('split-size'), 'the review entry point renders the export screen');
    assert.equal(control('split').value, 'no'); assert.equal(control('split-size').disabled, true, 'from the review screen the size starts disabled');
    control('split').value = 'phases'; control('split').dispatchEvent(new Event('change')); await settle();
    assert.equal(control('split-size').disabled, true, 'from the review screen «Por fases de energía» keeps it disabled');
    await f.navigate('playlists'); await settle();
    f.cardOptions().dispatchEvent(new Event('click')); await settle();
    assert.equal(control('split').value, 'no', 'the saved-playlist entry point starts again on «Sin dividir»');
    assert.equal(control('split-size').disabled, true, 'from a saved playlist the size starts disabled');
    control('split').value = 'every'; control('split').dispatchEvent(new Event('change')); await settle();
    assert.equal(control('split-size').disabled, false, '«Cada N pistas» enables it from the saved-playlist entry point');
    assert.deepEqual(f.exported, [], 'no choice of split starts an export');
  } finally { f.restore(); }
});
test('both new buttons follow the export gating: disabled while an operation runs (S2)', async () => {
  const gate = { hold: false }; let release;
  const f = await fixture({ listPlaylists: () => gate.hold ? new Promise((resolve) => { release = () => resolve([saved]); }) : Promise.resolve([saved]) });
  try {
    await f.navigate('prep'); f.generated(); await settle();
    await f.navigate('playlists'); await settle();
    assert.equal(f.get('export-review-options').disabled, false);
    assert.equal(f.cardOptions().disabled, false);
    gate.hold = true; f.click('refresh-playlists'); await settle();
    assert.equal(f.get('export-review').disabled, true, 'the quick export button it matches is disabled');
    assert.equal(f.get('export-review-options').disabled, true, 'the review options button obeys the busy gate');
    assert.equal(f.cardOptions().disabled, true, 'the card options button obeys the busy gate');
    release(); await settle();
    assert.equal(f.get('export-review').disabled, false);
    assert.equal(f.get('export-review-options').disabled, false);
    assert.equal(f.cardOptions().disabled, false);
  } finally { f.restore(); }
});
test('a review the core cannot export keeps both buttons disabled (S2)', async () => {
  const f = await fixture({ generatePrep: async () => detailed({ reviewId: '', savedPlaylistId: undefined, canSave: false }) });
  try {
    await f.navigate('prep'); f.generated(); await settle();
    assert.equal(f.get('export-review').disabled, true, 'there is no source to export');
    assert.equal(f.get('export-review-options').disabled, true, 'the options button shares the quick export gating');
  } finally { f.restore(); }
});
test('«Exportar a Serato» keeps starting one quick export from the card and the review (S2)', async () => {
  const f = await fixture();
  try {
    await f.navigate('playlists'); await settle();
    f.find('Exportar a Serato').dispatchEvent(new Event('click')); await settle();
    assert.deepEqual(f.exported, [{ source: { kind: 'saved', playlistId: '1' }, name: 'Guardada' }], 'the card still starts the quick export with its own source');
    assert.equal(f.get('page-title').textContent, 'Playlists guardadas', 'the quick export stays on the page');
    assert.equal(f.get('serato-export-source').textContent, OTHER_SOURCE, 'the export options screen was never opened');
    assert.equal(f.get('serato-quick-export-notice').textContent, 'Exportación cancelada', 'the quick notice reported the cancelled export');
    await f.openSaved();
    f.click('export-review'); await settle();
    assert.deepEqual(f.exported.at(-1), { source: { kind: 'saved', playlistId: '1' }, name: 'Guardada' }, 'the review button still exports the opened saved list');
    assert.equal(f.exported.length, 2, 'each click started exactly one export');
    assert.equal(f.get('page-title').textContent, 'Revisar y exportar', 'the review quick export does not navigate either');
  } finally { f.restore(); }
});
test('the saved card text keeps the actions it always had next to the new option (S2)', async () => {
  const f = await fixture();
  try {
    await f.navigate('playlists'); await settle();
    const captions = f.find('Exportar a Serato').parent.children.filter((node) => node.tagName === 'button').map((node) => node.textContent);
    assert.deepEqual(captions, ['Exportar a Serato', 'Opciones de exportación', 'Editar', 'Renombrar', 'Duplicar'], 'the new button joins the card without displacing the existing actions');
    assert.match(text(f.get('playlists-list')), /Guardada/);
  } finally { f.restore(); }
});
