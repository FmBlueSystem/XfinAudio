/**
 * S6 in the real app: a saved list the core answers with a `reviewId` is edited like a
 * generated one — its controls and the list assistant work, «Guardar cambios en la playlist»
 * saves it in place, and the short list, the alternatives and a `use_variant` stay away.
 * A read-only answer (no `reviewId`, `editable: false`) keeps the screen it always had.
 */
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
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
const all = (node) => [node, ...node.children.flatMap(all)];
const text = (node) => [node.textContent, ...node.children.map(text)].join(' ');
const tick = () => new Promise((resolve) => setImmediate(resolve));
const settle = async () => { for (let i = 0; i < 5; i++) await tick(); };
const prefs = (patch = {}) => ({ revision: 'a'.repeat(64), previewVolume: .25, watchLibrary: true, recoveryWarning: false, libraryLabels: ['DJ'], capabilities: { loudnessWriteback: false, providers: false, language: 'es' }, ...patch });
const status = (patch = {}) => ({ revision: 1, changeState: 'restored', watchState: 'active', rootCount: 1, watchedCount: 1, ...patch });
const tracks = ['a', 'b'].map((id) => ({ id: id.repeat(64), title: id, artist: 'DJ', bpm: 120, key: '8A', energy: 5, duration: 120, missing: false }));
const profileStatus = (patch = {}) => ({ state: 'complete', totalTracks: 2, readyCount: 2, spectralReadyCount: 2, danceabilityReadyCount: 2, edgeReadyCount: 2, pendingCount: 0, failedCount: 0, ...patch });
const completion = (patch = {}) => ({ cancelled: false, tracks, status: profileStatus(), completeCount: 2, incompleteCount: 0, ...patch });
const detailed = (patch = {}) => ({ reviewId: 'review', name: 'Set', variant: 'balanced', readiness: 'ready', tracks, warnings: [], blockers: [], qualityScore: .8, engineFacts: 'Local engine: 2 tracks', readinessSummary: 'Ready', readinessChecks: [{ label: 'Metadata', status: 'ready', detail: 'Complete' }], transitions: [{ index: 1, leftTrackId: tracks[0].id, rightTrackId: tracks[1].id, totalScore: .8, compatibilityScore: .9, mixabilityScore: .7, components: { bpm: 1, key: .8 }, explanations: ['Compatible'], warnings: [] }], protectedTrackIds: [], ...patch });
const prepSettings = (patch = {}) => ({ revision: 'a'.repeat(64), requiredTrackIds: [], excludedTrackIds: [], genreFocus: 'House', unavailableRequiredCount: 0, unavailableExcludedCount: 0, ...patch });
/** The two reviews S6 distinguishes: the opened list and the one an edit mints. */
const savedId = '12345678-1234-4123-8123-123456789012';
const editedId = '87654321-4321-4321-8321-210987654321';
const savedReview = (patch = {}) => detailed({ reviewId: savedId, name: 'Guardada', variant: 'saved', savedPlaylistId: '1', ...patch });
const saves = (patch = {}) => ({ id: '1', name: 'Guardada', trackCount: 2, ...patch });
let sequence = 0;
async function fixture(overrides = {}) {
  const previousDocument = globalThis.document; const previousWindow = globalThis.window; const elements = new Map(); const calls = []; let onStatus; let progress;
  const nodes = () => [...elements.values()].flatMap(all); const get = (id) => { const dynamic = nodes().find((node) => node.id === id); if (dynamic) return dynamic; if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  const routes = ['library', 'prep', 'preferences', 'playlists', 'editor', 'review', 'live', 'serato'].map((route) => { const button = new Element('button'); button.dataset.route = route; return button; });
  const api = {
    listLibrary: async () => ({ tracks, count: 2 }), getPrepCatalog: async () => ({ strategies: [] }), onProgress: (callback) => { progress = callback; return () => {}; },
    getPreferences: async () => prefs(), savePreferences: async (input) => ({ ...prefs(), ...input, revision: 'b'.repeat(64) }),
    getLibraryStatus: async () => status(), onLibraryStatus: (callback) => { onStatus = callback; return () => {}; },
    getProfileStatus: async () => profileStatus(), getProfileSettings: async () => ({ revision: 'a'.repeat(64), spectralCohesion: .5 }), saveProfileSettings: async (input) => ({ ...input, revision: 'b'.repeat(64) }), completeProfiles: async () => completion(),
    rescanLibrary: async () => ({ tracks, count: 2 }), setDraftDirty: async (dirty) => { calls.push(['dirty', dirty]); },
    listPlaylists: async () => [{ id: '1', name: 'Guardada', trackCount: 2, createdAt: '' }],
    openPlaylistEditor: async () => ({ id: '1', editId: 'edit', revision: 'r1', name: 'Guardada', tracks, missingTrackCount: 0 }), discardPlaylistEdit: async () => ({ id: '1', editId: 'edit', revision: 'r1', name: 'Guardada', tracks, missingTrackCount: 0 }),
    generatePrep: async (input) => { calls.push(['generate', input]); return detailed(); },
    reviewDetails: async (input) => { calls.push(['reviewDetails', input]); return savedReview({ reviewId: input.reviewId }); },
    reviewCompare: async (input) => { calls.push(['reviewCompare', input]); return { reviewId: input.reviewId, available: true, replacement: tracks[1], original: detailed(), proposed: detailed(), message: 'Preview only' }; },
    reviewRemove: async (input) => { calls.push(['reviewRemove', input]); return savedReview({ reviewId: editedId, name: 'Guardada actualizada', tracks: [tracks[1]] }); },
    reviewReorder: async (input) => { calls.push(['reviewReorder', input]); return savedReview({ reviewId: editedId, tracks: [...tracks].reverse() }); },
    selectPrepVariant: async (input) => detailed({ reviewId: `variant-${input.variant}`, variant: input.variant }),
    openPlaylist: async (input) => { calls.push(['open', input]); return savedReview({ warnings: ['Track count shortfall: selected 2 of 6 requested tracks'] }); },
    savePlaylist: async (input) => { calls.push(['savePlaylist', input]); return saves(input); },
    savePlaylistReview: async (input) => { calls.push(['savePlaylistReview', input]); return saves({ name: 'Guardada actualizada' }); },
    aiChatHistory: async () => ({ conversation: [], actions: [] }), aiChatReset: async () => ({ conversation: [], actions: [] }),
    prepareAiRequest: async (input) => ({ previewId: savedId, surface: 'chat', recipient: 'https://api.nan.builders/v1/chat/completions', disclosure: ['Se comparten títulos, artistas y transiciones, nunca rutas.'], requestPreview: input.request, firstTurn: true }),
    runAiRequest: async () => { throw new Error('unreachable'); }, inspectAiPayload: async () => { throw new Error('unreachable'); }, aiChatApply: async () => { throw new Error('unreachable'); },
    ...overrides,
  };
  globalThis.document = { getElementById: get, createElement: (tag) => new Element(tag), title: '', querySelectorAll: (selector) => selector === '[data-route]' || selector === '.nav-item' ? routes : [] };
  globalThis.window = Object.assign(new EventTarget(), { xfin: api }); get('metadata-filter').value = 'all'; get('prep-count').value = '2';
  await import(`../.out/renderer/app.js?savedReview=${++sequence}`); await settle();
  const click = (id) => get(id).dispatchEvent(new Event('click'));
  const navigate = async (route) => { routes.find((button) => button.dataset.route === route).dispatchEvent(new Event('click')); await settle(); };
  const openSaved = async () => {
    await navigate('playlists'); await settle();
    const card = nodes().find((node) => node.tagName === 'button' && node.textContent === 'Abrir playlist →');
    assert.ok(card, 'the saved playlist card is on the screen');
    card.dispatchEvent(new Event('click')); await settle();
  };
  const selectTrack = (index) => { const select = get('review-selected-track'); select.value = tracks[index].id; select.dispatchEvent(new Event('change')); };
  return { get, calls, nodes, click, navigate, openSaved, selectTrack, generated: () => { get('prep-form').dispatchEvent(new Event('submit', { cancelable: true })); }, restore: () => { window.dispatchEvent(new Event('beforeunload')); globalThis.document = previousDocument; globalThis.window = previousWindow; }, progress: (value) => progress(value), status: (value) => onStatus(value) };
}
test('an opened saved list is editable, keeps its label, gets the bot and offers no short list or alternatives', async () => {
  const f = await fixture();
  try {
    await f.openSaved();
    assert.equal(f.get('review-variant').textContent, 'PLAYLIST GUARDADA');
    assert.equal(f.get('generated-review-container').hidden, false, 'a saved list with a reviewId is editable');
    assert.equal(f.get('bot-window-root').hidden, false, 'it gets the list assistant like a generated list');
    assert.equal(f.get('variant-comparison').hidden, true, 'a saved list has no alternatives to compare');
    assert.equal(f.nodes().some((node) => node.id === 'review-short-list'), false, 'the short-list notice is not shown');
    assert.match(text(f.get('review-alerts')), /Se seleccionaron 2 de las 6 pistas solicitadas/, 'its warning keeps the translated line');
    assert.equal(f.get('save-review-changes').hidden, true, 'nothing to save before the first edit');
    assert.equal(f.get('save-form').hidden, false);
    assert.equal(f.get('review-save-summary').textContent, 'Guardar como playlist nueva');
    assert.equal(f.get('save-playlist').textContent, 'Guardar como playlist nueva');
    assert.equal(f.get('save-playlist').disabled, false);
  } finally { f.restore(); }
});
test('an edited saved list offers «Guardar cambios en la playlist», saves it in place and says its name', async () => {
  const f = await fixture();
  try {
    await f.openSaved();
    f.selectTrack(0);
    f.click('review-remove-0'); await settle();
    assert.deepEqual(f.calls.find(([kind]) => kind === 'reviewRemove')[1], { reviewId: savedId, trackId: tracks[0].id });
    assert.equal(f.get('save-review-changes').hidden, false, 'the list now has edits the core has not stored');
    assert.match(await readFile(new URL('../renderer/index.html', import.meta.url), 'utf8'), /id="save-review-changes"[^>]*>Guardar cambios en la playlist</, 'the button carries the S6 caption');
    f.click('save-review-changes'); await settle();
    assert.deepEqual(f.calls.find(([kind]) => kind === 'savePlaylistReview')[1], { reviewId: editedId }, 'it sends only the review id it saves');
    assert.equal(f.get('operation-label').textContent, 'Playlist guardada: Guardada actualizada');
    assert.equal(f.get('save-review-changes').hidden, true, 'the saved list has no pending edits any more');
  } finally { f.restore(); }
});
test('a saved list changed elsewhere says so in its own words, and the editor keeps its draft line', async () => {
  const conflict = Object.assign(new Error('[stale_edit] Playlist changed elsewhere'), { code: 'stale_edit' });
  const f = await fixture({ savePlaylistReview: async (input) => { f.calls.push(['savePlaylistReview', input]); throw conflict; } });
  try {
    await f.openSaved();
    f.selectTrack(0);
    f.click('review-remove-0'); await settle();
    f.click('save-review-changes'); await settle();
    assert.equal(f.get('operation-detail').textContent, 'La playlist cambió en otro lugar. Ábrela de nuevo para no perder cambios.');
    assert.doesNotMatch(f.get('operation-detail').textContent, /stale_edit|elsewhere|borrador/);
    assert.equal(f.get('save-review-changes').hidden, false, 'the edits are still unsaved');
  } finally { f.restore(); }
});
test('a read-only saved answer without a reviewId keeps the review screen read-only', async () => {
  const f = await fixture({ openPlaylist: async (input) => { f.calls.push(['open', input]); return detailed({ reviewId: '', variant: 'saved', name: 'Solo lectura', canSave: false }); } });
  try {
    await f.openSaved();
    assert.equal(f.get('review-variant').textContent, 'PLAYLIST GUARDADA');
    assert.equal(f.get('generated-review-container').hidden, true, 'no reviewId, no edits');
    assert.equal(f.get('bot-window-root').hidden, true, 'the assistant belongs to an editable list');
    assert.equal(f.get('save-form').hidden, true, 'the bridge refuses this save');
    assert.equal(f.get('save-review-changes').hidden, true);
  } finally { f.restore(); }
});
test('a generated list keeps its own save form, its alternatives and no in-place save', async () => {
  const f = await fixture({ generatePrep: async (input) => { f.calls.push(['generate', input]); return detailed({ reviewId: editedId, planId: 'plan-1', variants: [{ name: 'safe', description: 'Safe', trackCount: 2, readiness: 'ready', warnings: [], blockers: [], qualityScore: .8 }] }); } });
  try { await f.navigate('prep'); f.generated(); await settle();
    assert.equal(f.get('save-form').hidden, false);
    assert.equal(f.get('review-save-summary').textContent, 'Guardar esta lista en el equipo');
    assert.equal(f.get('save-playlist').textContent, 'Guardar playlist');
    assert.equal(f.get('save-playlist').disabled, false);
    assert.equal(f.get('variant-comparison').hidden, false);
    assert.equal(f.get('save-review-changes').hidden, true, 'a generated list is saved, not re-saved in place');
  } finally { f.restore(); }
});
