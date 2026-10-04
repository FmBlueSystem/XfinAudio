import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

class Element extends EventTarget {
  constructor(tag = 'div') { super(); this.tagName = tag; }
  textContent = ''; value = ''; checked = false; disabled = false; hidden = false; dataset = {}; children = []; attrs = {}; classes = new Set(); paused = true; duration = 0; currentTime = 0;
  classList = { toggle: (key, active) => active ? this.classes.add(key) : this.classes.delete(key), contains: (key) => this.classes.has(key) };
  setAttribute(key, value) { this.attrs[key] = value; } removeAttribute(key) { delete this.attrs[key]; }
  append(...nodes) { this.children.push(...nodes); } replaceChildren(...nodes) { this.children = nodes; } closest() { return null; } focus() {} pause() { this.paused = true; } load() {} async play() { this.paused = false; }
}
const all = (node) => [node, ...node.children.flatMap(all)];
const tick = () => new Promise((resolve) => setImmediate(resolve));
const settle = async () => { for (let i = 0; i < 12; i++) await tick(); };
const tracks = ['a', 'b'].map((id) => ({ id: id.repeat(64), title: id, artist: 'DJ', bpm: 120, key: '8A', energy: 5, duration: 120, missing: false }));
const prefs = () => ({ revision: 'a'.repeat(64), previewVolume: .25, watchLibrary: true, recoveryWarning: false, libraryLabels: ['DJ'], capabilities: { loudnessWriteback: false, providers: false, language: 'es' } });
const status = (patch = {}) => ({ revision: 5, changeState: 'restored', watchState: 'active', rootCount: 1, watchedCount: 1, ...patch });

let sequence = 0;
async function fixture(overrides = {}) {
  const previousDocument = globalThis.document; const previousWindow = globalThis.window;
  const elements = new Map(); const calls = [];
  const nodes = () => [...elements.values()].flatMap(all);
  const get = (id) => { const dynamic = nodes().find((node) => node.id === id); if (dynamic) return dynamic; if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  const routes = ['library', 'metadata', 'preferences', 'playlists', 'editor', 'review', 'live', 'serato'].map((route) => { const button = new Element('button'); button.dataset.route = route; return button; });
  const api = {
    listLibrary: async () => { calls.push(['library']); return { tracks, count: tracks.length }; },
    getPrepCatalog: async () => ({ strategies: [] }),
    onProgress: () => () => {},
    getPreferences: async () => prefs(),
    savePreferences: async (input) => ({ ...prefs(), ...input }),
    getLibraryStatus: async () => status(),
    onLibraryStatus: () => () => {},
    rescanLibrary: async () => { calls.push(['rescan']); return { tracks, count: tracks.length }; },
    chooseLibrary: async () => { calls.push(['choose']); return { tracks, count: tracks.length }; },
    ...overrides,
  };
  globalThis.document = { getElementById: get, createElement: (tag) => new Element(tag), title: '', querySelectorAll: (selector) => selector === '[data-route]' || selector === '.nav-item' ? routes : selector === '[data-mutation]' ? nodes().filter((node) => 'mutation' in node.dataset) : [] };
  globalThis.window = Object.assign(new EventTarget(), { xfin: api });
  get('metadata-filter').value = 'all'; get('prep-count').value = '2';
  await import(`../.out/renderer/app.js?libraryBoot=${++sequence}`);
  await settle();
  const click = (id) => get(id).dispatchEvent(new Event('click'));
  return { get, calls, click, restore: () => { globalThis.document = previousDocument; globalThis.window = previousWindow; } };
}

test('renderer supplies an explicit library recovery panel with a retry control', async () => {
  const html = await readFile(new URL('../renderer/index.html', import.meta.url), 'utf8');
  assert.match(html, /id="library-recovery"/);
  assert.match(html, /id="library-recovery-message"/);
  assert.match(html, /id="library-retry"/);
});

test('library bootstrap failure stays visible through idle work and reloads only through listLibrary on retry', async () => {
  let attempts = 0;
  const f = await fixture({
    listLibrary: async () => {
      attempts += 1;
      if (attempts === 1) throw { code: 'core_stopped' };
      return { tracks, count: tracks.length };
    },
  });
  try {
    assert.equal(attempts, 1);
    assert.equal(f.get('library-empty').hidden, false);
    assert.equal(f.get('library-recovery').hidden, false);
    assert.match(f.get('library-recovery-message').textContent, /servicio local|vuelve a intentarlo|no se pudo/i);
    assert.equal(f.get('library-retry').disabled, false);
    await settle();
    assert.equal(f.get('library-recovery').hidden, false, 'idle work must not hide the bootstrap failure');
    assert.match(f.get('library-recovery-message').textContent, /servicio local|vuelve a intentarlo|no se pudo/i);
    f.click('library-retry');
    await settle();
    assert.equal(attempts, 2);
    assert.equal(f.get('library-total').textContent, '2');
    assert.equal(f.get('library-recovery').hidden, true);
    assert.equal(f.get('operation-status').hidden, true, 'successful reload still hides the operation status');
    assert.equal(f.calls.some(([kind]) => kind === 'rescan' || kind === 'choose'), false, 'retry must not scan or open a folder');
  } finally { f.restore(); }
});

test('library retry is a safe no-op while the operation gate is busy', async () => {
  let attempts = 0; let release;
  const pending = new Promise((resolve) => { release = resolve; });
  const f = await fixture({
    listLibrary: async () => {
      attempts += 1;
      if (attempts === 1) throw { code: 'core_stopped' };
      await pending;
      return { tracks, count: tracks.length };
    },
  });
  try {
    await settle();
    f.click('library-retry');
    f.click('library-retry');
    assert.equal(attempts, 2, 'a second retry while busy must not start another load');
    release();
    await settle();
    assert.equal(f.get('library-recovery').hidden, true);
    assert.equal(f.get('library-total').textContent, '2');
  } finally { f.restore(); }
});
