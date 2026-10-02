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
  const routes = ['library', 'metadata'].map((name) => { const button = new Element(); button.dataset.route = name; return button; });
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
