import assert from 'node:assert/strict';
import test from 'node:test';
import { createLiveView } from '../.out/renderer/live-view.js';
class Element extends EventTarget {
  constructor(tag = 'div') { super(); this.tagName = tag; }
  children = []; attrs = {}; dataset = {}; textContent = ''; value = ''; disabled = false; hidden = false;
  setAttribute(key, value) { this.attrs[key] = String(value); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  set innerHTML(_) { throw new Error('Unsafe HTML'); }
}
const all = (node) => [node, ...node.children.flatMap(all)];
const text = (node) => [node.textContent, ...node.children.map(text)].join(' ');
function fixture(empty = false) {
  const previous = globalThis.document; globalThis.document = { createElement: (tag) => new Element(tag) }; const root = new Element(); const calls = []; let online = true; let busy = false;
  const track = (id) => ({ id, title: id, artist: 'Artista', bpm: 122, key: '8A', energy: 5, duration: 180 });
  const controller = { snapshot: { sessionId: 's1', revision: 1, sourceReviewId: 'r1', state: 'active', current: track('Actual'), history: [{ track: track('Anterior'), startedAt: '2026-10-01T10:00:00Z' }], candidates: [{ track: track('<script>Primera</script>'), score: 0.97, alerts: ['<img src=x> aviso'] }, { track: track('Segunda'), score: 0.81, alerts: [] }], elapsedSeconds: 62 }, valid: true, pending: false, error: '', refresh: async () => calls.push(['refresh']), clear: async () => calls.push(['clear']), advance: async (id) => calls.push(['advance', id]) };
  if (empty) controller.snapshot = null;
  const view = createLiveView(root, controller, { canAct: () => online && !busy, isConnected: () => online, play: (track) => calls.push(['play', track.id]) }); view.render();
  return { root, controller, calls, view, get: (id) => all(root).find((node) => node.id === `live-${id}`), nodes: () => all(root), disconnect: () => { online = false; view.render(); }, block: () => { busy = true; view.render(); }, restore: () => { view.dispose(); globalThis.document = previous; } };
}
test('accessible Spanish Live renders authoritative rank, scores, alerts, history and honest timing as text', () => {
  const f = fixture(); try {
    for (const expected of ['Actual', 'Anterior', '<script>Primera</script>', '0,97', '<img src=x> aviso', '1:02', 'manual']) assert.ok(text(f.root).includes(expected), expected);
    assert.ok(!f.nodes().some((node) => ['script', 'img', 'audio'].includes(node.tagName))); assert.equal(f.get('error').attrs.role, 'alert'); assert.ok(f.nodes().some((node) => node.attrs['aria-label']?.includes('Preescuchar'))); assert.equal(f.get('candidates').children.length, 2); assert.equal(f.get('history').children.length, 1);
  } finally { f.restore(); }
});
test('preview and manually marking next are independent actions, with no automatic playback', () => {
  const f = fixture(); try {
    const listen = f.nodes().find((node) => node.dataset.livePreview === '<script>Primera</script>'); const next = f.nodes().find((node) => node.dataset.liveNext === '<script>Primera</script>'); listen.dispatchEvent(new Event('click')); assert.deepEqual(f.calls, [['play', '<script>Primera</script>']]); next.dispatchEvent(new Event('click')); assert.deepEqual(f.calls.at(-1), ['advance', '<script>Primera</script>']); assert.equal(f.calls.filter(([type]) => type === 'play').length, 1);
    f.get('refresh').dispatchEvent(new Event('click')); f.get('clear').dispatchEvent(new Event('click')); assert.deepEqual(f.calls.slice(-2), [['refresh'], ['clear']]);
  } finally { f.restore(); }
});
test('core disconnect preserves explanatory snapshot but disables every action and pauses the timer', () => {
  const f = fixture(); try { f.disconnect(); assert.match(text(f.root), /conexión|desconectado/i); assert.equal(f.get('content').hidden, false); assert.ok(f.nodes().filter((node) => node.tagName === 'button').every((node) => node.disabled)); const count = f.calls.length; for (const button of f.nodes().filter((node) => node.tagName === 'button')) button.dispatchEvent(new Event('click')); assert.equal(f.calls.length, count); } finally { f.restore(); }
});
test('stale candidate controls cannot advance or play after refresh replaces the snapshot', () => {
  const f = fixture(); try {
    const next = f.nodes().find((node) => node.dataset.liveNext); const listen = f.nodes().find((node) => node.dataset.livePreview); f.controller.snapshot = { ...f.controller.snapshot, revision: 2, candidates: [] }; f.view.render(); next.dispatchEvent(new Event('click')); listen.dispatchEvent(new Event('click')); assert.deepEqual(f.calls, []);
    f.controller.valid = false; f.view.render(); assert.ok(f.nodes().filter((node) => node.dataset.livePreview).every((node) => node.disabled));
  } finally { f.restore(); }
});
test('empty and complete sessions remain explicit without fallback suggestions; repeated render keeps stable list nodes', () => {
  const f = fixture(); try { const child = f.get('candidates').children[0]; f.view.render(); assert.equal(f.get('candidates').children[0], child); f.controller.snapshot = { ...f.controller.snapshot, state: 'complete', candidates: [] }; f.view.render(); assert.match(text(f.root), /complet|no hay más/i); assert.equal(f.get('candidates').children.length, 0); f.controller.snapshot = null; f.view.render(); assert.equal(f.get('content').hidden, true); assert.equal(f.get('empty').hidden, false); assert.match(text(f.get('empty')), /revisada|lista/i); } finally { f.restore(); }
});
test('display timer runs only for a connected valid session and stops on clear, disconnect or disposal', () => {
  const interval = globalThis.setInterval; const clear = globalThis.clearInterval; let started = 0; let stopped = 0; globalThis.setInterval = () => ++started; globalThis.clearInterval = () => { stopped++; };
  const f = fixture(); try {
    assert.equal(started, 1); const snapshot = f.controller.snapshot; f.controller.snapshot = null; f.view.render(); assert.equal(stopped, 1); f.view.render(); assert.equal(started, 1);
    f.controller.snapshot = snapshot; f.view.render(); assert.equal(started, 2); f.disconnect(); assert.equal(stopped, 2); f.view.dispose(); assert.equal(stopped, 2);
  } finally { f.restore(); globalThis.setInterval = interval; globalThis.clearInterval = clear; }
});
test('app startup without Live never schedules a display timer', () => {
  const interval = globalThis.setInterval; let started = 0; globalThis.setInterval = () => ++started;
  const f = fixture(true); try { f.view.render(); assert.equal(started, 0); assert.equal(f.get('content').hidden, true); } finally { f.restore(); globalThis.setInterval = interval; }
});
