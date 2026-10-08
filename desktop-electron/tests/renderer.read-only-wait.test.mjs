import assert from 'node:assert/strict';
import test from 'node:test';
class Element extends EventTarget {
  constructor(tag = 'div') { super(); this.tagName = tag; }
  textContent = ''; value = ''; checked = false; disabled = false; hidden = false; dataset = {}; children = []; attrs = {}; classes = new Set(); paused = true; duration = 0; currentTime = 0;
  get options() { return this.children; } get selectedOptions() { return this.children.filter(node => node.selected); }
  classList = { toggle: (key, active) => active ? this.classes.add(key) : this.classes.delete(key), contains: (key) => this.classes.has(key) };
  setAttribute(key, value) { this.attrs[key] = value; } removeAttribute(key) { delete this.attrs[key]; }
  append(...nodes) { this.children.push(...nodes); } replaceChildren(...nodes) { this.children = nodes; } closest() { return null; } focus() { this.focused = true; } pause() { this.paused = true; } load() {} async play() { this.paused = false; }
}
const all = (node) => [node, ...node.children.flatMap(all)]; const text = (node) => [node.textContent, ...node.children.map(text)].join(' ');
const tick = () => new Promise((resolve) => setImmediate(resolve)); const settle = async () => { for (let i = 0; i < 5; i++) await tick(); };
const prefs = (patch = {}) => ({ revision: 'a'.repeat(64), previewVolume: .25, watchLibrary: true, recoveryWarning: false, libraryLabels: ['DJ'], capabilities: { loudnessWriteback: false, providers: false, language: 'es' }, ...patch });
const status = (patch = {}) => ({ revision: 1, changeState: 'restored', watchState: 'active', rootCount: 1, watchedCount: 1, ...patch });
const tracks = ['a', 'b'].map((id) => ({ id: id.repeat(64), title: id, artist: 'DJ', bpm: 120, key: '8A', energy: 5, duration: 120, missing: false }));
const metadata = () => ({ totalTracks: 2, completeCount: 0, incompleteCount: 2, gaps: { bpm: 2, camelot_key: 0, energy_level: 0 }, yearCoverage: { withReleaseYear: 0, withoutReleaseYear: 2 }, tracks: tracks.map((track, index) => ({ ...track, missingFields: ['bpm'], explanation: 'Revisar BPM', releaseYear: null, locked: false, priority: index + 1 })), repairPlan: 'Revisar fuentes', readOnly: true });
const strategy = { name: 'warmup', displayName: 'Calentamiento', description: 'Abre la sesión con energía creciente', requiresVibeMetadata: false };
let sequence = 0;
async function fixture(overrides = {}) {
  const previousDocument = globalThis.document; const previousWindow = globalThis.window; const elements = new Map(); const calls = []; let onStatus; let progress;
  const nodes = () => [...elements.values()].flatMap(all); const get = (id) => { const dynamic = nodes().find((node) => node.id === id); if (dynamic) return dynamic; if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  const routes = ['library', 'preferences', 'metadata', 'playlists', 'prep', 'editor', 'review', 'live', 'serato'].map((route) => { const button = new Element('button'); button.dataset.route = route; return button; });
  const api = {
    listLibrary: async () => { calls.push(['library']); return { tracks, count: 2 }; }, onProgress: (callback) => { progress = callback; return () => {}; },
    getPreferences: async () => { calls.push(['preferences']); return prefs(); }, savePreferences: async (input) => { calls.push(['savePreferences', input]); return prefs({ ...input, revision: 'b'.repeat(64) }); },
    getLibraryStatus: async () => { calls.push(['status']); return status(); }, onLibraryStatus: (callback) => { onStatus = callback; return () => {}; },
    rescanLibrary: async () => { calls.push(['rescan']); return { tracks, count: 2 }; }, setDraftDirty: async (dirty) => { calls.push(['dirty', dirty]); },
    listPlaylists: async () => { calls.push(['playlists']); return [{ id: '1', name: 'Set', trackCount: 2, createdAt: '' }]; },
    generatePrep: async () => ({ reviewId: 'review', name: 'Set', variant: 'balanced', readiness: 'ready', tracks, warnings: [], blockers: [] }),
    openLive: async () => ({ sessionId: 'live', revision: 0, sourceReviewId: 'review', state: 'active', current: tracks[0], history: [], candidates: [], elapsedSeconds: 0 }),
    chooseSeratoDestination: async () => ({ destinationId: 'dest', label: '_Serato_' }), previewSeratoExport: async () => ({ previewId: 'preview', sourceRevision: 'r', filename: 'Set.crate', destinationLabel: '_Serato_', trackCount: 2, readiness: 'ready', warnings: [], blockers: [], canCommit: true, tracks, backup: { required: false } }), ...overrides,
  };
  globalThis.document = { getElementById: get, createElement: (tag) => new Element(tag), title: '', querySelectorAll: (selector) => selector === '[data-route]' || selector === '.nav-item' ? routes : selector === '[data-mutation]' ? nodes().filter((node) => 'mutation' in node.dataset) : [], };
  globalThis.window = Object.assign(new EventTarget(), { xfin: api }); get('metadata-filter').value = 'all'; get('prep-count').value = '2';
  await import(`../.out/renderer/app.js?readOnlyWait=${++sequence}`); await settle();
  const click = (id) => get(id).dispatchEvent(new Event('click')); const navigate = async (route) => { routes.find((button) => button.dataset.route === route).dispatchEvent(new Event('click')); await settle(); };
  return { get, calls, nodes, click, navigate, status, restore: () => { window.dispatchEvent(new Event('beforeunload')); globalThis.document = previousDocument; globalThis.window = previousWindow; } };
}

test('the inline catalog read refreshes a read-only screen while an exclusive task holds the gate', async () => {
  let catalogCalls = 0; let finish;
  const f = await fixture({
    getPrepCatalog: async () => { catalogCalls += 1; if (catalogCalls === 1) throw new Error('[busy] Another task is still running'); return { strategies: [strategy] }; },
    getMetadataReport: () => new Promise((resolve) => { finish = resolve; }),
  });
  try {
    // Boot could not read the catalog, so the retry stays offered on the prep screen.
    assert.equal(f.get('catalog-retry').hidden, false);
    assert.match(f.get('strategy-hint').textContent, /No se pudo cargar el catálogo/);
    await f.navigate('metadata');
    assert.equal(f.get('generate-prep').disabled, true, 'the exclusive task must own the gate');
    f.calls.length = 0;
    f.click('catalog-retry'); await settle();
    assert.equal(catalogCalls, 2, 'the inline catalog read must still be requested');
    assert.equal(f.get('prep-strategy').children.length, 2, 'the read-only strategy list must refresh during the wait');
    assert.equal(f.get('prep-strategy').children[1].textContent, 'Calentamiento');
    assert.equal(f.get('prep-strategy').children[1].value, 'warmup');
    assert.equal(f.get('catalog-retry').hidden, true, 'a successful inline read clears the retry hint');
    // Refreshing a read-only screen must never re-enable a control that changes data.
    assert.equal(f.get('prep-strategy').disabled, true);
    assert.equal(f.get('save-playlist').disabled, true);
    finish(metadata()); await settle();
    assert.equal(f.get('metadata-worklist-export-serato').tagName, 'button');
  } finally { f.restore(); }
});

test('navigation during an exclusive task explains the deferred refresh instead of looking broken', async () => {
  let finish;
  const f = await fixture({ getMetadataReport: () => new Promise((resolve) => { finish = resolve; }) });
  try {
    await f.navigate('metadata');
    assert.equal(f.get('generate-prep').disabled, true, 'the exclusive task must own the gate');
    f.calls.length = 0;
    await f.navigate('playlists');
    assert.equal(f.calls.some(([kind]) => kind === 'playlists'), false, 'the blocked read must stay deferred');
    assert.equal(f.get('operation-label').textContent, 'Revisando metadatos…', 'the running task keeps naming itself');
    assert.match(f.get('operation-detail').textContent, /La pantalla «Playlists guardadas» se actualizará cuando termine la operación en curso/);
    assert.equal(f.get('save-playlist').disabled, true);
    assert.equal(f.get('generate-prep').disabled, true);
    finish(metadata()); await settle();
    assert.equal(f.get('metadata-worklist-export-serato').tagName, 'button');
    assert.equal(f.calls.filter(([kind]) => kind === 'playlists').length, 1, 'the deferred read resumes once the host is free');
  } finally { f.restore(); }
});
