import assert from 'node:assert/strict';
import test from 'node:test';

class Element extends EventTarget {
  constructor(tag = 'div') { super(); this.tagName = tag; }
  textContent = ''; value = ''; max = 0; checked = false; disabled = false; hidden = false; dataset = {}; children = []; attrs = {}; classes = new Set(); paused = true; duration = 0; currentTime = 0;
  classList = { toggle: (key, active) => active ? this.classes.add(key) : this.classes.delete(key), contains: (key) => this.classes.has(key) };
  setAttribute(key, value) { this.attrs[key] = value; } removeAttribute(key) { delete this.attrs[key]; }
  append(...nodes) { this.children.push(...nodes); } replaceChildren(...nodes) { this.children = nodes; } closest() { return null; } focus() {} pause() { this.paused = true; } load() {} async play() { this.paused = false; }
}
const all = (node) => [node, ...node.children.flatMap(all)];
const text = (node) => [node.textContent, ...node.children.map(text)].join(' ');
const tick = () => new Promise((resolve) => setImmediate(resolve));
const settle = async () => { for (let i = 0; i < 6; i++) await tick(); };
const tracks = ['a', 'b'].map((id) => ({ id: id.repeat(64), title: id, artist: 'DJ', bpm: 120, key: '8A', energy: 5, duration: 120, missing: false }));
const review = (patch = {}) => ({ reviewId: 'review', name: 'Set', variant: 'balanced', readiness: 'ready', tracks, warnings: [], blockers: [], ...patch });
const status = (patch = {}) => ({ revision: 1, changeState: 'restored', watchState: 'active', rootCount: 1, watchedCount: 1, ...patch });
const prefs = (patch = {}) => ({ revision: 'a'.repeat(64), previewVolume: .25, watchLibrary: true, recoveryWarning: false, libraryLabels: ['DJ'], capabilities: { loudnessWriteback: false, providers: false, language: 'es' }, ...patch });
const profileStatus = (patch = {}) => ({ state: 'partial', totalTracks: 2, readyCount: 0, spectralReadyCount: 0, danceabilityReadyCount: 0, edgeReadyCount: 0, pendingCount: 2, failedCount: 0, ...patch });
const completion = (patch = {}) => ({ cancelled: false, tracks, status: profileStatus({ state: 'complete', readyCount: 2, spectralReadyCount: 2, danceabilityReadyCount: 2, edgeReadyCount: 2, pendingCount: 0 }), completeCount: 2, incompleteCount: 0, ...patch });

// ---- the shipped module, driven directly ---------------------------------------------

const { createOperationStatus, stageLine } = await import('../.out/renderer/operation-status.js');

function viewOf({ settleMilliseconds = 4000 } = {}) {
  const pending = [];
  const mapped = new Map();
  const root = new Element('section');
  const trigger = new Element('button');
  const previous = globalThis.document;
  globalThis.document = {
    createElement: (tag) => new Element(tag),
    getElementById: (id) => { if (!mapped.has(id)) mapped.set(id, new Element()); return mapped.get(id); },
  };
  const view = createOperationStatus(root, { schedule: (run, milliseconds) => pending.push({ run, milliseconds }), settleMilliseconds });
  const find = (id) => all(root).find((node) => node.id === id) ?? mapped.get(id);
  return { view, root, trigger, find, pending, restore: () => { globalThis.document = previous; } };
}

test('a stage line only claims the parts it knows', () => {
  assert.equal(stageLine(null), '');
  assert.equal(stageLine({}), '');
  assert.equal(stageLine({ index: 2, total: 2 }), 'Paso 2 de 2');
  assert.equal(stageLine({ label: 'Escaneando la biblioteca', current: 5, totalCount: 10 }), 'Escaneando la biblioteca · 5 de 10');
  assert.equal(stageLine({ index: 3, total: 2, label: 'Completando perfiles', current: 340, totalCount: 1200 }), 'Paso 2 de 2 · Completando perfiles · 340 de 1 200');
  assert.equal(stageLine({ index: 0, total: 0, current: 5, totalCount: 0 }), '');
});

test('running names the operation, its numbered stage and its counts, and marks the starting button', async () => {
  const f = viewOf(); try {
    f.view.start('Completando perfiles locales…', f.trigger, { index: 2, total: 2 });
    assert.equal(f.root.hidden, false);
    assert.equal(f.root.attrs['aria-busy'], 'true');
    assert.equal(f.root.classes.has('is-running'), true);
    assert.equal(f.view.cancel.hidden, true, 'the cancel control keeps its own visibility');
    assert.equal(f.find('operation-label').textContent, 'Completando perfiles locales…');
    assert.equal(f.find('operation-stage').textContent, 'Paso 2 de 2');
    assert.equal(f.find('operation-progress').hidden, false);
    assert.equal('value' in f.find('operation-progress').attrs, false, 'no counts yet means an indeterminate bar');
    assert.equal(f.trigger.attrs['aria-busy'], 'true');
    assert.equal(f.trigger.classes.has('is-working'), true);

    f.view.stage({ index: 2, total: 2, label: 'Completando perfiles', current: 340, totalCount: 1200 });
    f.view.progress(340, 1200);
    assert.equal(f.find('operation-stage').textContent, 'Paso 2 de 2 · Completando perfiles · 340 de 1 200');
    assert.equal(f.find('operation-progress').value, 340);
    assert.equal(f.find('operation-progress').max, 1200);
    assert.equal(f.find('operation-progress').hidden, false);
  } finally { f.restore(); }
});

test('a chained job keeps one running region across its numbered steps and stops marking the old button', async () => {
  const f = viewOf(); try {
    f.view.start('Volviendo a escanear bibliotecas…', f.trigger, { index: 1, total: 2 });
    assert.equal(f.find('operation-stage').textContent, 'Paso 1 de 2');
    const next = new Element('button');
    f.view.start('Completando perfiles locales…', next, { index: 2, total: 2 });
    assert.equal(f.find('operation-stage').textContent, 'Paso 2 de 2');
    assert.equal(f.trigger.classes.has('is-working'), false);
    assert.equal(f.trigger.attrs['aria-busy'], 'false');
    assert.equal(next.classes.has('is-working'), true);
    assert.equal(f.root.attrs['aria-busy'], 'true');
  } finally { f.restore(); }
});

test('done shows a green check with the result and settles into a discreet line', async () => {
  const f = viewOf(); try {
    f.view.start('Leyendo metadatos…', f.trigger);
    f.view.done('Biblioteca actualizada', '10 391 pistas');
    assert.equal(f.root.attrs['aria-busy'], 'false');
    assert.equal(f.root.classes.has('is-running'), false);
    assert.equal(f.root.classes.has('is-done'), true);
    assert.equal(f.find('operation-indicator').textContent, '✓');
    assert.equal(f.find('operation-label').textContent, 'Biblioteca actualizada');
    assert.equal(f.find('operation-detail').textContent, '10 391 pistas');
    assert.equal(f.find('operation-progress').hidden, true);
    assert.equal(f.trigger.classes.has('is-working'), false);
    assert.equal(f.pending.length, 1);
    assert.equal(f.pending[0].milliseconds, 4000);
    assert.equal(f.root.classes.has('is-settled'), false);
    f.pending[0].run();
    assert.equal(f.root.classes.has('is-settled'), true);
    assert.equal(f.find('operation-label').textContent, 'Biblioteca actualizada', 'the last result stays readable');
    assert.equal(f.root.hidden, false);
  } finally { f.restore(); }
});

test('error and cancellation stay red with their reason until the next operation', async () => {
  const f = viewOf(); try {
    f.view.start('Guardando preferencias…', f.trigger);
    f.view.fail('No se pudo completar la operación', 'El servicio local no responde');
    assert.equal(f.root.classes.has('is-error'), true);
    assert.equal(f.root.classes.has('is-running'), false);
    assert.equal(f.root.attrs['aria-busy'], 'false');
    assert.equal(f.find('operation-indicator').textContent, '!');
    assert.equal(f.find('operation-detail').textContent, 'El servicio local no responde');
    assert.equal(f.pending.length, 0, 'an error is never replaced on a timer');
    f.view.cancelled('Operación cancelada', 'Puedes volver a intentarlo cuando quieras');
    assert.equal(f.root.classes.has('is-error'), false);
    assert.equal(f.root.classes.has('is-cancelled'), true);
    assert.equal(f.find('operation-indicator').textContent, '×');
    assert.equal(f.find('operation-detail').textContent, 'Puedes volver a intentarlo cuando quieras');
    f.view.start('Guardando preferencias…', f.trigger);
    assert.equal(f.root.classes.has('is-cancelled'), false);
    assert.equal(f.root.classes.has('is-running'), true);
    assert.equal(f.find('operation-indicator').textContent, '');
  } finally { f.restore(); }
});

test('a neutral notice never claims success and hiding clears the last line', async () => {
  const f = viewOf(); try {
    f.view.notice('Servicio local disponible', 'XfinAudio volvió a conectar con tu biblioteca.');
    assert.equal(f.root.classes.has('is-done'), false);
    assert.equal(f.find('operation-indicator').textContent, '');
    assert.equal(f.root.attrs['aria-busy'], 'false');
    f.view.hide();
    assert.equal(f.root.hidden, true);
    assert.equal(f.root.classes.has('is-running'), false);
    assert.equal(f.find('operation-detail').textContent, '');
  } finally { f.restore(); }
});

// ---- the app wiring users actually see ------------------------------------------------

let sequence = 0;
async function fixture(overrides = {}) {
  const previousDocument = globalThis.document; const previousWindow = globalThis.window; const elements = new Map(); const calls = []; let progress;
  const nodes = () => [...elements.values()].flatMap(all); const get = (id) => { const dynamic = nodes().find((node) => node.id === id); if (dynamic) return dynamic; if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  const routes = ['library', 'prep', 'review', 'playlists', 'editor', 'preferences', 'live', 'serato'].map((route) => { const button = new Element('button'); button.dataset.route = route; return button; });
  const api = {
    listLibrary: async () => { calls.push(['library']); return { tracks, count: 2 }; }, getPrepCatalog: async () => ({ strategies: [] }), onProgress: (callback) => { progress = callback; return () => {}; },
    getPreferences: async () => prefs(), savePreferences: async (input) => { calls.push(['savePreferences', input]); return prefs({ ...input, revision: 'b'.repeat(64) }); },
    getLibraryStatus: async () => status(), onLibraryStatus: () => () => {},
    getProfileStatus: async () => profileStatus(), getProfileSettings: async () => ({ revision: 'a'.repeat(64), spectralCohesion: .5 }), saveProfileSettings: async (input) => ({ ...input, revision: 'b'.repeat(64) }),
    rescanLibrary: async () => { calls.push(['rescan']); return { tracks, count: 2 }; }, completeProfiles: async () => { calls.push(['completeProfiles']); return completion(); }, cancelCurrent: async () => { calls.push(['cancel']); return { cancelled: true }; },
    setDraftDirty: async () => {}, listPlaylists: async () => { calls.push(['playlists']); return []; }, generatePrep: async () => { calls.push(['prep']); return review(); },
    ...overrides,
  };
  globalThis.document = { getElementById: get, createElement: (tag) => new Element(tag), title: '', querySelectorAll: (selector) => selector === '[data-route]' || selector === '.nav-item' ? routes : selector === '[data-mutation]' ? nodes().filter((node) => 'mutation' in node.dataset) : [] };
  globalThis.window = Object.assign(new EventTarget(), { xfin: api }); get('metadata-filter').value = 'all'; get('prep-count').value = '2';
  await import(`../.out/renderer/app.js?operationStatus=${++sequence}`); await settle();
  const click = (id) => get(id).dispatchEvent(new Event('click')); const navigate = async (route) => { routes.find((button) => button.dataset.route === route).dispatchEvent(new Event('click')); await settle(); };
  return { get, calls, nodes, click, navigate, progress: (value) => progress(value), submitPrep: async () => { get('prep-form').dispatchEvent(new Event('submit', { cancelable: true })); await settle(); }, restore: () => { window.dispatchEvent(new Event('beforeunload')); globalThis.document = previousDocument; globalThis.window = previousWindow; } };
}

test('scan and automatic profile completion are the two numbered steps of one job', async () => {
  let finishScan; let finishProfiles;
  const f = await fixture({ rescanLibrary: () => new Promise((resolve) => { finishScan = resolve; }), completeProfiles: () => new Promise((resolve) => { finishProfiles = resolve; }) }); try {
    f.click('library-status-rescan'); await settle();
    assert.equal(f.get('operation-status').attrs['aria-busy'], 'true');
    assert.equal(f.get('operation-status').classes.has('is-running'), true);
    assert.equal(f.get('operation-stage').textContent, 'Paso 1 de 2');
    f.progress({ jobId: 'scan-job', operation: 'library.rescan', phase: 'scan', current: 5, total: 10, message: 'a.flac' });
    assert.equal(f.get('operation-stage').textContent, 'Paso 1 de 2 · Escaneando la biblioteca · 5 de 10');
    assert.equal(f.get('operation-progress').value, 5);
    finishScan({ tracks, count: 2 }); await settle();
    assert.equal(f.get('operation-stage').textContent, 'Paso 2 de 2', 'completion is the second step of the same job');
    assert.equal(f.get('operation-status').classes.has('is-running'), true);
    f.progress({ jobId: 'profiles-job', operation: 'profiles.complete', phase: 'profiles', stage: 'danceability', current: 1, total: 2, readyCount: 1, failedCount: 0 });
    assert.match(f.get('operation-label').textContent, /bailabilidad/i);
    assert.equal(f.get('operation-stage').textContent, 'Paso 2 de 2 · Completando bailabilidad · 1 de 2');
    assert.equal(f.get('operation-progress').value, 1);
    assert.equal(f.get('operation-progress').max, 2);
    finishProfiles(completion()); await settle();
    assert.equal(f.get('operation-status').attrs['aria-busy'], 'false');
    assert.equal(f.get('operation-status').classes.has('is-done'), true);
    assert.equal(f.get('operation-indicator').textContent, '✓');
    assert.match(f.get('operation-label').textContent, /Perfiles completados/);
  } finally { f.restore(); }
});

test('set generation shows the core stage names in Spanish and marks the Generate button as working', async () => {
  let finishPrep;
  const f = await fixture({ generatePrep: () => new Promise((resolve) => { finishPrep = resolve; }) }); try {
    await f.navigate('prep'); await f.submitPrep();
    assert.equal(f.get('generate-prep').attrs['aria-busy'], 'true');
    assert.equal(f.get('generate-prep').classes.has('is-working'), true);
    assert.equal(f.get('operation-stage').textContent, '');
    assert.equal(f.get('operation-progress').hidden, false);
    assert.equal('value' in f.get('operation-progress').attrs, false, 'no counts yet means an indeterminate bar');
    f.progress({ jobId: 'prep-job', operation: 'prep.generate', phase: 'prep', current: 1, total: 3, stage: 'Preparando alternativa equilibrada' });
    assert.equal(f.get('operation-label').textContent, 'Preparando alternativa equilibrada');
    assert.doesNotMatch(f.get('operation-label').textContent, /Preparando selección/);
    assert.equal(f.get('operation-stage').textContent, 'Paso 2 de 3 · Preparando alternativa equilibrada · 1 de 3');
    assert.equal(f.get('operation-progress').value, 1);
    assert.equal(f.get('operation-progress').max, 3);
    finishPrep(review()); await settle();
    assert.equal(f.get('generate-prep').classes.has('is-working'), false);
    assert.equal(f.get('generate-prep').attrs['aria-busy'], 'false');
    assert.equal(f.get('operation-status').classes.has('is-done'), true);
    assert.match(f.get('operation-label').textContent, /Selección preparada/);
  } finally { f.restore(); }
});

test('hosts that announce the started job refresh the running state instead of dropping it', async () => {
  let finish;
  const f = await fixture({ rescanLibrary: () => new Promise((resolve) => { finish = resolve; }) }); try {
    f.click('library-status-rescan'); await settle();
    f.progress({ jobId: 'job', operation: 'library.rescan', phase: 'started', message: 'Procesando…' });
    assert.equal(f.get('operation-status').classes.has('is-running'), true);
    assert.equal(f.get('operation-status').attrs['aria-busy'], 'true');
    assert.equal(f.get('operation-progress').hidden, false);
    finish({ tracks, count: 2 }); await settle();
  } finally { f.restore(); }
});

test('an operation without progress shows an indeterminate running state and a done state', async () => {
  let finish;
  const f = await fixture({ listPlaylists: () => new Promise((resolve) => { finish = resolve; }) }); try {
    await f.navigate('playlists');
    f.click('refresh-playlists'); await settle();
    assert.equal(f.get('operation-status').classes.has('is-running'), true);
    assert.equal(f.get('operation-status').attrs['aria-busy'], 'true');
    assert.equal(f.get('operation-progress').hidden, false);
    assert.equal('value' in f.get('operation-progress').attrs, false);
    finish([]); await settle();
    assert.equal(f.get('operation-status').attrs['aria-busy'], 'false');
    assert.equal(f.get('operation-status').classes.has('is-done'), true);
    assert.equal(f.get('operation-indicator').textContent, '✓');
    assert.equal(f.get('operation-label').textContent, 'Playlists actualizadas');
  } finally { f.restore(); }
});

test('a cancelled operation is red with its reason and the next operation replaces it', async () => {
  let finish;
  const f = await fixture({ generatePrep: () => new Promise((resolve) => { finish = resolve; }), listPlaylists: async () => [] }); try {
    await f.navigate('prep'); await f.submitPrep();
    f.click('cancel-operation'); await settle();
    finish(review()); await settle();
    assert.equal(f.get('operation-status').classes.has('is-cancelled'), true);
    assert.equal(f.get('operation-status').classes.has('is-running'), false);
    assert.match(f.get('operation-detail').textContent, /volver a intentarlo|recuperar/i);
    assert.equal(f.get('operation-status').attrs['aria-busy'], 'false');
    await f.navigate('playlists'); f.click('refresh-playlists'); await settle();
    assert.equal(f.get('operation-status').classes.has('is-cancelled'), false);
    assert.equal(f.get('operation-status').classes.has('is-done'), true, 'the next operation publishes its own result');
  } finally { f.restore(); }
});

test('a failed operation stays red with its reason until the next one', async () => {
  let fail = true;
  const f = await fixture({ savePreferences: async (input) => { if (fail) throw { code: 'preferences_unavailable' }; return prefs({ ...input, revision: 'b'.repeat(64) }); } }); try {
    await f.navigate('preferences'); f.get('preferences-volume').value = '.5'; f.get('preferences-volume').dispatchEvent(new Event('input')); f.click('preferences-save'); await settle();
    assert.equal(f.get('operation-status').classes.has('is-error'), true);
    assert.equal(f.get('operation-indicator').textContent, '!');
    assert.match(f.get('operation-label').textContent, /No se pudo completar la operación/);
    assert.ok(f.get('operation-detail').textContent.length > 0, 'the reason is kept on screen');
    fail = false; f.click('preferences-save'); await settle();
    assert.equal(f.get('operation-status').classes.has('is-error'), false);
    assert.equal(f.get('operation-status').classes.has('is-done'), true);
  } finally { f.restore(); }
});
