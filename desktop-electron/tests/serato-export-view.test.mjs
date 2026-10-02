import assert from 'node:assert/strict';
import test from 'node:test';
import { createSeratoExportView } from '../.out/renderer/serato-export-view.js';
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
function fixture() {
  const previous = globalThis.document; globalThis.document = { createElement: (tag) => new Element(tag) }; const root = new Element(); const calls = []; let available = true;
  const controller = { source: { kind: 'saved', playlistId: 'saved-1' }, name: 'Sesión', destination: { destinationId: 'destination-1', label: 'Subcrates' }, preview: null, receipt: null, pending: null, canPreview: true, canCommit: false, error: '', status: '', setName: (value) => calls.push(['name', value]), chooseDestination: async () => calls.push(['choose']), requestPreview: async () => calls.push(['preview']), commit: async () => calls.push(['commit']), reveal: async () => calls.push(['reveal']) };
  const render = createSeratoExportView(root, controller, { canAct: () => available }); render();
  return { root, controller, calls, render, get: (id) => all(root).find((node) => node.id === `serato-export-${id}`), block: () => { available = false; render(); }, restore: () => { globalThis.document = previous; } };
}
test('Serato-only view has Spanish explicit controls and safely renders preview metadata', () => {
  const f = fixture(); try {
    assert.match(text(f.root), /_Serato_|Subcrates/); assert.doesNotMatch(text(f.root), /staging|Rekordbox|Traktor|VirtualDJ/); assert.ok(all(f.root).some((node) => node.tagName === 'label' && node.attrs.for === 'serato-export-name'));
    f.controller.preview = { previewId: 'p', filename: '<img src=x>.crate', destinationLabel: 'Subcrates', trackCount: 2, readiness: 'needs_review', warnings: ['Revisa el salto de BPM'], blockers: [], canCommit: true, backup: { required: true }, tracks: [{ title: '<script>x</script>', artist: 'A' }, { title: 'Segunda', artist: 'B' }] }; f.controller.canCommit = true; f.render();
    for (const expected of ['<img src=x>.crate', '<script>x</script>', 'Revisa el salto de BPM', 'Revisión recomendada', 'copia de seguridad']) assert.ok(text(f.root).includes(expected), expected);
    assert.ok(!all(f.root).some((node) => ['script', 'img'].includes(node.tagName))); assert.equal(f.get('commit').disabled, false); assert.equal(f.get('tracks').children.length, 2);
  } finally { f.restore(); }
});
test('view dispatches preview and export separately and disables changes while committing without Cancel', () => {
  const f = fixture(); try {
    f.get('choose').dispatchEvent(new Event('click')); f.get('preview').dispatchEvent(new Event('click')); f.get('commit').dispatchEvent(new Event('click')); assert.deepEqual(f.calls, [['choose'], ['preview'], ['commit']]);
    f.controller.pending = 'commit'; f.render(); for (const id of ['choose', 'preview', 'commit', 'name']) assert.equal(f.get(id).disabled, true); assert.match(text(f.root), /no.*cancel|finalizar/i); assert.ok(!all(f.root).some((node) => node.tagName === 'button' && /cancel/i.test(node.textContent)));
  } finally { f.restore(); }
});
test('blocked preview warnings and receipt remain visible; reveal is receipt-only', () => {
  const f = fixture(); try {
    f.controller.preview = { filename: 'Set.crate', destinationLabel: 'Subcrates', trackCount: 0, readiness: 'blocked', warnings: ['Aviso'], blockers: ['Archivo ausente'], backup: { required: false }, tracks: [] }; f.controller.error = 'Necesitas otra vista previa'; f.render(); assert.equal(f.get('commit').disabled, true); assert.match(text(f.root), /Archivo ausente/); assert.equal(f.get('error').attrs.role, 'alert');
    f.controller.source = null; f.controller.receipt = { receiptId: 'r', filename: 'Confirmado.crate', destinationLabel: 'Subcrates', trackCount: 2, validated: true, backupCreated: true }; f.render(); assert.equal(f.get('receipt').hidden, false); assert.match(text(f.get('receipt')), /Confirmado.crate/); assert.match(text(f.get('receipt')), /validado|validación/i); f.get('reveal').dispatchEvent(new Event('click')); assert.deepEqual(f.calls, [['reveal']]); f.block(); assert.equal(f.get('reveal').disabled, true);
  } finally { f.restore(); }
});
