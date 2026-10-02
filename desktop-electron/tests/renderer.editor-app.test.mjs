import assert from 'node:assert/strict';
import test from 'node:test';
class Element extends EventTarget {
  constructor(tag = 'div') { super(); this.tagName = tag; }
  textContent = ''; value = ''; disabled = false; hidden = false; dataset = {}; children = []; attrs = {}; classes = new Set();
  classList = { toggle: (key, active) => active ? this.classes.add(key) : this.classes.delete(key), contains: (key) => this.classes.has(key) };
  setAttribute(key, value) { this.attrs[key] = value; } removeAttribute(key) { delete this.attrs[key]; }
  append(...nodes) { this.children.push(...nodes); } replaceChildren(...nodes) { this.children = nodes; } closest() { return null; } focus() {}
  set innerHTML(_) { throw new Error('No HTML'); }
}
const tick = () => new Promise((resolve) => setImmediate(resolve));
const all = (node) => [node, ...node.children.flatMap(all)];
const text = (node) => [node.textContent, ...node.children.map(text)].join(' ');
const click = (node) => { assert.ok(node); node.dispatchEvent(new Event('click')); };
let sequence = 0;
async function fixture(overrides = {}) {
  const oldDocument = globalThis.document; const oldWindow = globalThis.window; const elements = new Map();
  const nodes = () => [...elements.values()].flatMap(all);
  const get = (id) => { const dynamic = nodes().find((node) => node.id === id); if (dynamic) return dynamic; if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  const routes = ['library', 'playlists', 'editor', 'serato'].map((route) => { const node = new Element('button'); node.dataset.route = route; return node; });
  const tracks = [{ id: 'a'.repeat(64), title: 'Uno', artist: 'Artista', bpm: 120, key: '8A', energy: 5, duration: 60, missing: false }, { id: 'b'.repeat(64), title: 'Dos', artist: 'Artista', bpm: 121, key: '8A', energy: 6, duration: 60, missing: true }];
  let saved = [{ id: '1', name: 'Original', trackCount: 2, createdAt: '' }, { id: '2', name: 'Otra', trackCount: 2, createdAt: '' }];
  const snapshot = (id = '1', patch = {}) => ({ id, editId: `edit-${id}`, revision: 'r1', name: saved.find((item) => item.id === id)?.name ?? 'Original', tracks, missingTrackCount: 1, ...patch });
  const calls = []; let progress;
  const api = {
    listLibrary: async () => ({ tracks, count: 2 }), getPrepCatalog: async () => ({ strategies: [] }), onProgress: (callback) => { progress = callback; return () => {}; },
    listPlaylists: async () => saved,
    setDraftDirty: async (dirty) => calls.push(['dirty', dirty]),
    openPlaylistEditor: async ({ playlistId }) => { calls.push(['open', playlistId]); return snapshot(playlistId); },
    savePlaylistEdit: async (input) => { calls.push(['save', input]); return snapshot('1', { editId: 'new', name: input.name, tracks: input.trackIds.map((id) => tracks.find((track) => track.id === id)) }); },
    discardPlaylistEdit: async (input) => { calls.push(['discard', input]); return snapshot(); },
    previewPlaylistEdit: async (input) => { calls.push(['preview', input]); return { editId: 'edit-1', revision: 'r1', previewId: 'p1', tracks: [tracks[0]], assessment: { description: 'Real', readiness: 'needs_review', qualityScore: .5, warnings: ['Aviso'] } }; },
    renamePlaylist: async (input) => { calls.push(['rename', input]); const result = { ...saved[0], name: input.name }; saved = [result, saved[1]]; return result; },
    duplicatePlaylist: async (input) => { calls.push(['duplicate', input]); return { ...saved[0], id: '3', name: 'Original (copia)' }; },
    chooseSeratoDestination: async () => { calls.push(['destination']); return { destinationId: 'dest', label: '_Serato_' }; },
    previewSeratoExport: async (input) => { calls.push(['exportPreview', input]); return { previewId: 'preview', sourceRevision: 'r', filename: 'Set.crate', destinationLabel: '_Serato_', trackCount: 2, readiness: 'needs_review', warnings: [], blockers: [], canCommit: true, tracks: tracks.map(t => ({ ...t, missing: false })), backup: { required: false } }; },
    commitSeratoExport: async (input) => { calls.push(['exportCommit', input]); return { receiptId: 'receipt', filename: 'Set.crate', destinationLabel: '_Serato_', trackCount: 2, validated: true, backupCreated: false }; },
    revealSeratoExport: async (input) => calls.push(['reveal', input]),
    chooseLibrary: async () => { calls.push(['scan']); return null; }, ...overrides,
  };
  globalThis.document = { getElementById: get, createElement: (tag) => new Element(tag), title: '', querySelectorAll: (selector) => selector === '[data-route]' || selector === '.nav-item' ? routes : selector === '[data-mutation]' ? nodes().filter((node) => 'mutation' in node.dataset) : [] };
  globalThis.window = Object.assign(new EventTarget(), { xfin: api }); get('metadata-filter').value = 'all';
  await import(`../.out/renderer/app.js?editorApp=${++sequence}`); await tick();
  const navigate = async (route) => { click(routes.find((node) => node.dataset.route === route)); await tick(); };
  const action = (caption, index = 0) => all(get('playlists-list').children[index]).find((node) => node.tagName === 'button' && node.textContent === caption);
  return { get, calls, navigate, action, nodes, progress: (event) => progress(event), restore: () => { globalThis.document = oldDocument; globalThis.window = oldWindow; } };
}
test('saved cards offer bounded rename, duplicate and edit with no implicit draft save', async () => {
  const f = await fixture(); try {
    await f.navigate('playlists'); click(f.action('Renombrar')); const input = f.nodes().find((node) => node.id === 'playlist-name-1'); assert.ok(input); input.value = 'Nuevo';
    f.nodes().find((node) => node.id === 'playlist-rename-1').dispatchEvent(new Event('submit', { cancelable: true })); await tick();
    assert.deepEqual(f.calls.find(([kind]) => kind === 'rename'), ['rename', { playlistId: '1', name: 'Nuevo' }]); assert.match(text(f.get('playlists-list')), /Nuevo/);
    click(f.action('Duplicar')); click(f.action('Duplicar')); await tick(); assert.equal(f.calls.filter(([kind]) => kind === 'duplicate').length, 1); assert.match(text(f.get('playlists-list')), /copia/);
    click(f.action('Editar', 1)); await tick(); assert.equal(globalThis.document.title, 'XfinAudio · Editar playlist'); assert.equal(f.calls.filter(([kind]) => kind === 'save').length, 0);
  } finally { f.restore(); }
});
test('actual app retains dirty draft across navigation and requires cancel or explicit discard on another set', async () => {
  const f = await fixture(); try {
    await f.navigate('playlists'); click(f.action('Editar')); await tick(); const input = f.get('editor-name'); input.value = 'Mi borrador'; input.dispatchEvent(new Event('input')); assert.equal(f.calls.at(-1)[1], true);
    await f.navigate('library'); await f.navigate('playlists'); click(f.action('Editar')); await tick(); assert.equal(f.get('editor-name').value, 'Mi borrador'); assert.equal(f.calls.filter(([kind]) => kind === 'open').length, 1);
    await f.navigate('playlists'); click(f.action('Editar', 1)); await tick(); assert.equal(f.get('editor-switch').hidden, false); click(f.get('editor-switch-cancel')); assert.equal(f.get('editor-name').value, 'Mi borrador');
    await f.navigate('playlists'); click(f.action('Editar', 1)); await tick(); click(f.get('editor-switch-discard')); await tick(); assert.equal(f.get('editor-name').value, 'Otra'); assert.equal(f.get('editor-dirty').textContent, 'Sin cambios pendientes');
  } finally { f.restore(); }
});
test('dirty draft blocks library rescan and failed save preserves editable state', async () => {
  const f = await fixture({ savePlaylistEdit: async () => { throw new Error("Error invoking remote method 'xfin:action': Error: [stale_edit] Saved playlist changed /Users/private/music"); } }); try {
    await f.navigate('playlists'); click(f.action('Editar')); await tick(); const input = f.get('editor-name'); input.value = 'Conservar'; input.dispatchEvent(new Event('input'));
    click(f.get('choose-library')); await tick(); assert.equal(f.calls.filter(([kind]) => kind === 'scan').length, 0);
    click(f.get('editor-save')); await tick(); assert.equal(f.get('editor-name').value, 'Conservar'); assert.equal(f.get('editor-save').disabled, false); assert.match(f.get('editor-error').textContent, /cambi[oó]/); assert.equal(f.get('editor-dirty').textContent, 'Cambios sin guardar'); assert.match(f.get('operation-detail').textContent, /playlist.*cambió/i); assert.doesNotMatch(f.get('operation-detail').textContent, /xfin:action|stale_edit|\/Users|Saved playlist/);
  } finally { f.restore(); }
});

test('core disconnect preserves dirty draft text and disables editor mutations', async () => {
  const f = await fixture(); try {
    await f.navigate('playlists'); click(f.action('Editar')); await tick(); const input = f.get('editor-name'); input.value = 'Conservar sin conexión'; input.dispatchEvent(new Event('input'));
    f.progress({ operation: 'core', phase: 'error', message: 'Core stopped' }); assert.equal(f.get('editor-name').value, 'Conservar sin conexión'); assert.equal(f.get('editor-save').disabled, true); assert.equal(f.get('editor-name').disabled, true); assert.equal(f.get('editor-dirty').textContent, 'Cambios sin guardar');
  } finally { f.restore(); }
});

test('starting a new scan clears a clean editor session even if folder selection is dismissed', async () => {
  const f = await fixture(); try {
    await f.navigate('playlists'); click(f.action('Editar')); await tick(); assert.equal(f.get('editor-container').children[0].hidden, true);
    click(f.get('choose-library')); await tick(); assert.equal(f.get('editor-container').children[0].hidden, false);
    await f.navigate('playlists'); click(f.action('Editar')); await tick(); assert.equal(f.calls.filter(([kind]) => kind === 'open').length, 2);
  } finally { f.restore(); }
});

test('saved Serato export requires destination, preview and separate commit and retains receipt across navigation', async () => {
  let finish; const f = await fixture({ commitSeratoExport: () => new Promise(resolve => { finish = resolve; }) }); try {
    await f.navigate('playlists'); click(f.action('Exportar a Serato')); await tick(); assert.equal(document.title, 'XfinAudio · Exportar a Serato');
    click(f.get('serato-export-choose')); await tick(); click(f.get('serato-export-preview')); await tick();
    assert.deepEqual(f.calls.find(([kind]) => kind === 'exportPreview')[1], { source: { kind: 'saved', playlistId: '1' }, destinationId: 'dest', name: 'Original' });
    assert.equal(f.calls.some(([kind]) => kind === 'exportCommit'), false); assert.equal(f.get('serato-export-commit').disabled, false);
    click(f.get('serato-export-commit')); await tick(); assert.equal(f.get('cancel-operation').hidden, true); await f.navigate('library');
    finish({ receiptId: 'receipt', filename: 'Set.crate', destinationLabel: '_Serato_', trackCount: 2, validated: true, backupCreated: false }); await tick();
    assert.equal(document.title, 'XfinAudio · Biblioteca'); await f.navigate('serato'); assert.equal(f.get('serato-export-receipt').hidden, false); click(f.get('serato-export-reveal')); await tick(); assert.deepEqual(f.calls.at(-1), ['reveal', { receiptId: 'receipt' }]);
  } finally { f.restore(); }
});
test('dirty editor prevents exporting the old saved version until explicitly saved or discarded', async () => {
 const f = await fixture(); try {
  await f.navigate('playlists'); click(f.action('Editar')); await tick(); f.get('editor-name').value = 'Sin guardar'; f.get('editor-name').dispatchEvent(new Event('input'));
  await f.navigate('playlists'); click(f.action('Exportar a Serato')); await tick(); assert.equal(document.title, 'XfinAudio · Editar playlist'); assert.match(f.get('operation-detail').textContent, /[Gg]uarda o descarta/); assert.equal(f.calls.some(([kind]) => kind === 'destination'), false);
 } finally { f.restore(); }
});
test('conditional last-export access reopens the retained receipt offline without host calls or source changes',async()=>{
 const f=await fixture();try{
  assert.equal(f.get('resume-last-export').hidden,true);
  await f.navigate('playlists');click(f.action('Exportar a Serato'));await tick();click(f.get('serato-export-choose'));await tick();click(f.get('serato-export-preview'));await tick();click(f.get('serato-export-commit'));await tick();
  assert.equal(f.get('resume-last-export').hidden,false);const receipt=f.get('serato-export-receipt');const source=f.get('serato-export-source').textContent;const name=f.get('serato-export-name').value;
  await f.navigate('library');f.progress({operation:'core',phase:'error',message:'offline'});const before=JSON.stringify(f.calls);
  click(f.get('resume-last-export'));await tick();assert.equal(document.title,'XfinAudio · Exportar a Serato');assert.equal(f.get('serato-export-receipt'),receipt);assert.equal(receipt.hidden,false);assert.equal(f.get('serato-export-source').textContent,source);assert.equal(f.get('serato-export-name').value,name);assert.equal(JSON.stringify(f.calls),before);assert.equal(f.get('serato-export-commit').disabled,true);assert.equal(f.get('serato-export-reveal').disabled,true);
 }finally{f.restore();}
});
test('conditional resume editor opens the same offline draft without reopening or enabling mutation',async()=>{
 const f=await fixture();try{
  assert.equal(f.get('resume-editor').hidden,true);await f.navigate('playlists');click(f.action('Editar'));await tick();const name=f.get('editor-name');name.value='Borrador conservado';name.dispatchEvent(new Event('input'));assert.equal(f.get('resume-editor').hidden,false);
  await f.navigate('library');f.progress({operation:'core',phase:'error',message:'offline'});const before=JSON.stringify(f.calls);click(f.get('resume-editor'));await tick();assert.equal(document.title,'XfinAudio · Editar playlist');assert.equal(f.get('editor-name'),name);assert.equal(name.value,'Borrador conservado');assert.equal(f.get('editor-dirty').textContent,'Cambios sin guardar');assert.equal(name.disabled,true);assert.equal(f.get('editor-save').disabled,true);assert.equal(JSON.stringify(f.calls),before);
 }finally{f.restore();}
});
