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
let sequence = 0;
async function fixture(overrides = {}) {
  const previousDocument = globalThis.document; const previousWindow = globalThis.window; const elements = new Map(); const calls = []; let onStatus; let progress; let statusUnsubscribed = false;
  const nodes = () => [...elements.values()].flatMap(all); const get = (id) => { const dynamic = nodes().find((node) => node.id === id); if (dynamic) return dynamic; if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  const routes = ['library', 'preferences', 'playlists', 'editor', 'review', 'live', 'serato'].map((route) => { const button = new Element('button'); button.dataset.route = route; return button; });
  const api = {
    listLibrary: async () => { calls.push(['library']); return { tracks, count: 2 }; }, getPrepCatalog: async () => ({ strategies: [] }), onProgress: (callback) => { progress = callback; return () => {}; },
    getPreferences: async () => { calls.push(['preferences']); return prefs(); }, savePreferences: async (input) => { calls.push(['savePreferences', input]); return prefs({ ...input, revision: 'b'.repeat(64) }); },
    getLibraryStatus: async () => { calls.push(['status']); return status(); }, onLibraryStatus: (callback) => { onStatus = callback; return () => { statusUnsubscribed = true; }; },
    rescanLibrary: async () => { calls.push(['rescan']); return { tracks, count: 2 }; }, setDraftDirty: async (dirty) => { calls.push(['dirty', dirty]); },
    listPlaylists: async () => [{ id: '1', name: 'Set', trackCount: 2, createdAt: '' }], openPlaylistEditor: async () => ({ id: '1', editId: 'edit', revision: 'r1', name: 'Set', tracks, missingTrackCount: 0 }), discardPlaylistEdit: async () => ({ id: '1', editId: 'edit', revision: 'r1', name: 'Set', tracks, missingTrackCount: 0 }),
    generatePrep: async () => ({ reviewId: 'review', name: 'Set', variant: 'balanced', readiness: 'ready', tracks, warnings: [], blockers: [] }),
    openLive: async () => ({ sessionId: 'live', revision: 0, sourceReviewId: 'review', state: 'active', current: tracks[0], history: [], candidates: [{ track: tracks[1], score: 1, alerts: [] }], elapsedSeconds: 0 }),
    chooseSeratoDestination: async () => ({ destinationId: 'dest', label: '_Serato_' }), previewSeratoExport: async () => ({ previewId: 'preview', sourceRevision: 'r', filename: 'Set.crate', destinationLabel: '_Serato_', trackCount: 2, readiness: 'ready', warnings: [], blockers: [], canCommit: true, tracks, backup: { required: false } }), ...overrides,
  };
  globalThis.document = { getElementById: get, createElement: (tag) => new Element(tag), title: '', querySelectorAll: (selector) => selector === '[data-route]' || selector === '.nav-item' ? routes : selector === '[data-mutation]' ? nodes().filter((node) => 'mutation' in node.dataset) : [] };
  globalThis.window = Object.assign(new EventTarget(), { xfin: api }); get('metadata-filter').value = 'all'; get('prep-count').value = '2';
  await import(`../.out/renderer/app.js?preferencesApp=${++sequence}`); await settle();
  const click = (id) => get(id).dispatchEvent(new Event('click')); const navigate = async (route) => { routes.find((button) => button.dataset.route === route).dispatchEvent(new Event('click')); await settle(); };
  return { get, calls, nodes, click, navigate, event: (value) => { assert.equal(typeof onStatus, 'function'); onStatus(value); }, offline: () => progress({ operation: 'core', phase: 'error', message: '/private/core' }), statusUnsubscribed: () => statusUnsubscribed, generate: async () => { get('prep-form').dispatchEvent(new Event('submit', { cancelable: true })); await settle(); }, restore: () => { window.dispatchEvent(new Event('beforeunload')); globalThis.document = previousDocument; globalThis.window = previousWindow; } };
}
test('bootstrap serializes preferences/status after library and late persisted volume respects touched footer', async () => {
  let finish; const f = await fixture({ listLibrary: () => new Promise((resolve) => { finish = resolve; }) }); try {
    assert.equal(f.calls.some(([kind]) => kind === 'preferences'), false); assert.equal(f.get('audio-player').volume, .7); f.get('player-volume').value = '.6'; f.get('player-volume').dispatchEvent(new Event('input')); finish({ tracks, count: 2 }); await settle();
    assert.equal(f.calls.filter(([kind]) => kind === 'preferences').length, 1); assert.equal(f.calls.filter(([kind]) => kind === 'status').length, 1); assert.equal(f.get('audio-player').volume, .6); assert.match(f.get('library-status-changes').textContent, /reinicio/);
  } finally { f.restore(); }
});
test('preferences edits are local, preserve navigation draft, and explicit save applies volume without autoplay', async () => {
  const f = await fixture(); try { assert.equal(f.get('audio-player').volume, .25); await f.navigate('preferences'); assert.equal(document.title, 'XfinAudio · Preferencias'); f.get('preferences-volume').value = '.4'; f.get('preferences-volume').dispatchEvent(new Event('input')); assert.equal(f.get('audio-player').volume, .25); await f.navigate('library'); await f.navigate('preferences'); assert.equal(f.get('preferences-volume').value, '0.4'); f.click('preferences-save'); await settle(); assert.equal(f.get('audio-player').volume, .4); assert.equal(f.get('audio-player').paused, true); f.get('player-volume').value = '.8'; f.get('player-volume').dispatchEvent(new Event('input')); f.click('preferences-refresh'); await settle(); assert.equal(f.get('audio-player').volume, .8); } finally { f.restore(); }
});
test('editor and preference dirtiness aggregate so discarding one does not permit dirty close', async () => {
  const f = await fixture(); try { await f.navigate('preferences'); f.get('preferences-volume').value = '.3'; f.get('preferences-volume').dispatchEvent(new Event('input')); await f.navigate('playlists'); f.nodes().find((node) => node.tagName === 'button' && node.textContent === 'Editar').dispatchEvent(new Event('click')); await settle(); f.get('editor-name').value = 'Borrador'; f.get('editor-name').dispatchEvent(new Event('input')); f.click('preferences-discard'); assert.equal(f.calls.filter(([kind]) => kind === 'dirty').at(-1)[1], true); f.click('editor-discard'); await settle(); assert.equal(f.calls.filter(([kind]) => kind === 'dirty').at(-1)[1], false); } finally { f.restore(); }
});
test('manual registered-root rescan invalidates review and uses existing cancellation lifecycle', async () => {
  let finish; const f = await fixture({ rescanLibrary: () => new Promise((resolve) => { finish = resolve; }) }); try { await f.generate(); assert.equal(f.get('review-content').hidden, false); f.click('library-status-rescan'); assert.equal(f.get('review-content').hidden, true); assert.equal(f.get('cancel-operation').hidden, false); assert.equal(f.get('library-status-rescan').disabled, true); finish({ tracks, count: 2 }); await settle(); assert.equal(f.get('library-status-rescan').disabled, false); } finally { f.restore(); }
});
test('changed notifications preserve dirty editor but invalidate Live/Serato; watch failure alone stays clean', async () => {
  const f = await fixture(); try { await f.generate(); f.click('start-live'); await settle(); assert.equal(f.get('live-content').hidden, false); f.click('export-review'); f.click('serato-export-choose'); await settle(); f.click('serato-export-preview'); await settle(); assert.equal(f.get('serato-export-proposal').hidden, false);
    await f.navigate('playlists'); f.nodes().find((node) => node.tagName === 'button' && node.textContent === 'Editar').dispatchEvent(new Event('click')); await settle(); f.get('editor-name').value = 'Conservar'; f.get('editor-name').dispatchEvent(new Event('input'));
    f.event(status({ revision: 3, changeState: 'changed' })); assert.equal(f.get('editor-name').value, 'Conservar'); assert.equal(f.get('live-content').hidden, true); assert.equal(f.get('serato-export-proposal').hidden, true); assert.equal(f.get('review-content').hidden, true); f.click('library-status-rescan'); await settle(); assert.equal(f.calls.some(([kind]) => kind === 'rescan'), false);
    f.event(status({ revision: 4, changeState: 'clean', watchState: 'unavailable', watchedCount: 0 })); assert.match(f.get('library-status-changes').textContent, /Escaneo completado/); assert.match(f.get('library-status-watch').textContent, /futuros/);
  } finally { f.restore(); }
});
test('late status reads and old notifications never overwrite a newer revision or hide offline errors', async () => {
  let finish; const f = await fixture({ getLibraryStatus: () => new Promise((resolve) => { finish = resolve; }) }); try { f.event(status({ revision: 7, changeState: 'changed' })); finish(status({ revision: 2, changeState: 'clean' })); await settle(); assert.match(f.get('library-status-changes').textContent, /Se han detectado cambios/); f.event(status({ revision: 3, changeState: 'clean' })); assert.match(f.get('library-status-changes').textContent, /Se han detectado cambios/); f.offline(); f.event(status({ revision: 8, changeState: 'clean', watchState: 'paused' })); assert.match(f.get('library-status-watch').textContent, /pausa/); assert.equal(f.get('operation-label').textContent, 'Servicio local desconectado'); assert.equal(f.get('library-status-rescan').disabled, true); assert.equal(f.get('preferences-save').disabled, true); } finally { f.restore(); } assert.equal(f.statusUnsubscribed(), true);
});
test('a library change during Prep suppresses its late now-stale review', async () => {
  let finish; const f = await fixture({ generatePrep: () => new Promise((resolve) => { finish = resolve; }) }); try { f.get('prep-form').dispatchEvent(new Event('submit', { cancelable: true })); f.event(status({ revision: 2, changeState: 'changed' })); finish({ reviewId: 'old', name: 'Old', variant: 'balanced', readiness: 'ready', tracks, warnings: [], blockers: [] }); await settle(); assert.equal(f.get('review-content').hidden, true); assert.equal(f.get('save-playlist').disabled, true); } finally { f.restore(); }
});
test('cancelled rescan retains partial library and does not manufacture a clean status', async () => {
  let finish; let reads = 0; let cancels = 0; const f = await fixture({ listLibrary: async () => ({ tracks: ++reads === 1 ? tracks : tracks.slice(0, 1), count: reads === 1 ? 2 : 1 }), rescanLibrary: () => new Promise((resolve) => { finish = resolve; }), cancelCurrent: async () => { cancels++; } }); try {
    f.event(status({ revision: 2, changeState: 'changed' })); f.click('library-status-rescan'); f.click('cancel-operation'); assert.equal(cancels, 1); finish({ tracks, count: 2 }); await settle(); assert.equal(f.get('library-total').textContent, '1'); assert.match(f.get('library-status-changes').textContent, /Se han detectado cambios/); assert.equal(f.get('review-content').hidden, true);
  } finally { f.restore(); }
});
test('actual stale preference save keeps draft and footer session volume until explicit recovery', async () => {
  const f = await fixture({ savePreferences: async () => { throw new Error('Error invoking remote method: [stale_settings] /Users/private/settings'); } }); try {
    await f.navigate('preferences'); f.get('preferences-volume').value = '.5'; f.get('preferences-volume').dispatchEvent(new Event('input')); f.click('preferences-save'); await settle(); assert.equal(f.get('preferences-volume').value, '0.5'); assert.equal(f.get('audio-player').volume, .25); assert.equal(f.get('preferences-save').disabled, true); assert.match(f.get('preferences-error').textContent, /descarta.*actualiza/i); assert.doesNotMatch(f.get('operation-detail').textContent, /remote method|Users|stale_settings/);
  } finally { f.restore(); }
});
