import assert from 'node:assert/strict';
import test from 'node:test';

// The library start screen must offer the generated review the core recovered
// after a restart (S6), and report the exact notice when the library changed.

class Element extends EventTarget {
  constructor(tag = 'div') { super(); this.tagName = tag; }
  textContent = ''; value = ''; checked = false; disabled = false; hidden = false; dataset = {}; children = []; attrs = {}; classes = new Set();
  classList = { toggle: (key, active) => active ? this.classes.add(key) : this.classes.delete(key), contains: (key) => this.classes.has(key) };
  setAttribute(key, value) { this.attrs[key] = value; } removeAttribute(key) { delete this.attrs[key]; }
  append(...nodes) { this.children.push(...nodes); } replaceChildren(...nodes) { this.children = nodes; } closest() { return null; } focus() {} pause() {} load() {}
}
const all = (node) => [node, ...node.children.flatMap(all)];
const tick = () => new Promise((resolve) => setImmediate(resolve));
const settle = async () => { for (let index = 0; index < 16; index++) await tick(); };
const tracks = ['a', 'b', 'c'].map((letter, index) => ({ id: letter.repeat(64), title: letter.toUpperCase(), artist: 'DJ', bpm: 120 + index, key: '8A', energy: 5, duration: 180, missing: false }));
const planId = 'e80f5eca-8a03-4ed3-b832-c05e9be6566c';
const variants = ['safe', 'balanced', 'adventurous'].map((name) => ({ name, description: name, trackCount: 3, readiness: 'ready', warnings: [], blockers: [], qualityScore: 0.8 }));
const review = (patch = {}) => ({ reviewId: 'c0ffee00-0000-4000-8000-000000000001', planId, variants, tracks, warnings: [], blockers: [], name: 'Lista en curso', variant: 'balanced', readiness: 'ready', ...patch });
const notice = 'La lista en curso ya no se puede recuperar porque la biblioteca cambió';

let sequence = 0;
async function fixture(overrides = {}) {
  const previousDocument = globalThis.document; const previousWindow = globalThis.window;
  const elements = new Map(); const calls = [];
  const nodes = () => [...elements.values()].flatMap(all);
  const get = (id) => { const dynamic = nodes().find((node) => node.id === id); if (dynamic) return dynamic; if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  const routes = ['library', 'metadata', 'prep', 'playlists', 'editor', 'review', 'live', 'serato'].map((route) => { const button = new Element('button'); button.dataset.route = route; return button; });
  const api = {
    listLibrary: async () => ({ tracks, count: tracks.length }),
    getPrepCatalog: async () => ({ strategies: [] }),
    onProgress: () => () => {},
    cancelCurrent: async () => ({}),
    reviewResume: async () => { calls.push(['resume']); return { available: false, review: null, dropped: false }; },
    ...overrides,
  };
  globalThis.document = {
    getElementById: get, createElement: (tag) => new Element(tag), title: '',
    querySelectorAll: (selector) => selector === '[data-route]' || selector === '.nav-item' ? routes : selector === '[data-mutation]' ? nodes().filter((node) => 'mutation' in node.dataset) : [],
  };
  globalThis.window = Object.assign(new EventTarget(), { xfin: api });
  get('metadata-filter').value = 'all'; get('prep-count').value = '2';
  await import(`../.out/renderer/app.js?reviewRecovery=${++sequence}`);
  await settle();
  const click = (id) => get(id).dispatchEvent(new Event('click'));
  return { get, calls, click, restore: () => { globalThis.document = previousDocument; globalThis.window = previousWindow; } };
}

test('the start screen offers the recovered list and opens it without a second core call', async () => {
  const current = review();
  let resumeCalls = 0;
  const f = await fixture({ reviewResume: async () => { resumeCalls += 1; return { available: true, review: current, dropped: false }; } });
  try {
    assert.equal(resumeCalls, 1);
    assert.equal(f.get('resume-review').hidden, false);
    assert.equal(f.get('resume-review').textContent, 'Continuar con la lista en curso');
    assert.equal(f.get('session-resume').hidden, false);
    assert.equal(f.get('operation-status').hidden, true);
    f.click('resume-review');
    await settle();
    assert.equal(f.get('review-content').hidden, false);
    assert.equal(f.get('review-name').textContent, 'Lista en curso');
    assert.match(f.get('review-track-count').textContent, /3 pistas/);
    assert.equal(f.get('review-table').children.length > 0, true);
    assert.equal(f.get('resume-review').hidden, true, 'an opened list is no longer only an offer');
    assert.equal(resumeCalls, 1, 'opening the recovered list must not call the core again');
  } finally { f.restore(); }
});

test('a changed library drops the offer and says the exact notice', async () => {
  const f = await fixture({ reviewResume: async () => ({ available: false, review: null, dropped: true }) });
  try {
    assert.equal(f.get('resume-review').hidden, true, 'nothing unrecoverable is offered');
    assert.equal(f.get('session-resume').hidden, true);
    assert.equal(f.get('operation-status').hidden, false);
    assert.equal(f.get('operation-label').textContent, notice);
  } finally { f.restore(); }
});

test('without a list in progress nothing is offered and nothing is claimed', async () => {
  const f = await fixture();
  try {
    assert.equal(f.calls.length, 1);
    assert.equal(f.get('resume-review').hidden, true);
    assert.equal(f.get('session-resume').hidden, true);
    assert.equal(f.get('operation-label').textContent, '');
  } finally { f.restore(); }
});
