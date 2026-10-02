import assert from 'node:assert/strict';
import test from 'node:test';
import { createPreferencesView } from '../.out/renderer/preferences-view.js';
class Element extends EventTarget {
  constructor(tag = 'div') { super(); this.tagName = tag; }
  children = []; attrs = {}; textContent = ''; value = ''; checked = false; disabled = false; hidden = false;
  setAttribute(key, value) { this.attrs[key] = String(value); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  set innerHTML(_) { throw new Error('Unsafe HTML'); }
}
const all = (node) => [node, ...node.children.flatMap(all)];
const text = (node) => [node.textContent, ...node.children.map(text)].join(' ');
function fixture() {
  const previous = globalThis.document; globalThis.document = { createElement: (tag) => new Element(tag) }; let available = true; const calls = []; const root = new Element();
  const controller = { snapshot: { revision: 'a'.repeat(64), previewVolume: 0.8, watchLibrary: true, recoveryWarning: true, libraryLabels: ['<img src=x> Colección'], capabilities: { loudnessWriteback: false, providers: false, language: 'es' } }, dirty: false, pending: false, canSave: false, error: '', setVolume: (value) => calls.push(['volume', value]), setWatchLibrary: (value) => calls.push(['watch', value]), save: async () => calls.push(['save']), discard: () => calls.push(['discard']), load: async () => calls.push(['load']) };
  const render = createPreferencesView(root, controller, { canAct: () => available }); render();
  return { root, controller, calls, render, get: (id) => all(root).find((node) => node.id === `preferences-${id}`), block: () => { available = false; render(); }, restore: () => { globalThis.document = previous; } };
}
test('preferences expose only real accessible initial preview level and watch controls, preserving text-only labels', () => {
  const f = fixture(); try {
    for (const expected of ['inicial', 'preescucha', '80', 'sesión', 'pausa', 'credenciales', '<img src=x> Colección']) assert.ok(text(f.root).includes(expected), expected);
    const inputs = all(f.root).filter((node) => node.tagName === 'input'); assert.equal(inputs.length, 2); for (const suffix of ['volume', 'watch']) assert.ok(all(f.root).some((node) => node.tagName === 'label' && node.attrs.for === `preferences-${suffix}`));
    assert.equal(f.get('volume').min, '0'); assert.equal(f.get('volume').max, '1'); assert.equal(f.get('watch').type, 'checkbox'); assert.equal(f.get('recovery').hidden, false); assert.ok(!all(f.root).some((node) => ['img', 'script', 'select'].includes(node.tagName)));
  } finally { f.restore(); }
});
test('stable inputs dispatch local edits and explicit save/discard/refresh separately', () => {
  const f = fixture(); try {
    const volume = f.get('volume'); f.render(); assert.equal(f.get('volume'), volume); volume.value = '0.25'; volume.dispatchEvent(new Event('input')); f.get('watch').checked = false; f.get('watch').dispatchEvent(new Event('change')); assert.deepEqual(f.calls, [['volume', 0.25], ['watch', false]]);
    f.controller.dirty = f.controller.canSave = true; f.render(); for (const id of ['save', 'discard', 'refresh']) f.get(id).dispatchEvent(new Event('click')); assert.deepEqual(f.calls.slice(-3), [['save'], ['discard'], ['load']]); assert.match(text(f.root), /sin guardar/);
  } finally { f.restore(); }
});
test('offline and pending controls are disabled while draft/recovery/error stay visible', () => {
  const f = fixture(); try { f.controller.dirty = true; f.controller.error = 'Tu borrador se conserva'; f.block(); assert.equal(f.get('error').attrs.role, 'alert'); assert.match(text(f.root), /Tu borrador se conserva/); for (const node of all(f.root).filter((node) => ['button', 'input'].includes(node.tagName))) { assert.equal(node.disabled, true); node.dispatchEvent(new Event(node.type === 'checkbox' ? 'change' : node.tagName === 'input' ? 'input' : 'click')); } assert.deepEqual(f.calls, []); assert.equal(f.get('volume').value, '0.8'); } finally { f.restore(); }
});
test('implemented loudness capability points to Sonoridad while providers and credentials remain paused', () => {
  const f = fixture(); try { f.controller.snapshot.capabilities.loudnessWriteback = true; f.render(); assert.match(text(f.root), /Sonoridad/); assert.doesNotMatch(text(f.root), /etiquetas por sonoridad y los proveedores siguen en pausa/); assert.match(text(f.root), /proveedores.*pausa/); } finally { f.restore(); }
});
test('implemented provider capability directs explicit configuration to IA opcional',()=>{const f=fixture();try{f.controller.snapshot.capabilities.providers=true;f.render();assert.match(text(f.root),/IA opcional/);assert.doesNotMatch(text(f.root),/proveedores siguen en pausa/);}finally{f.restore();}});
