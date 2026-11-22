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
  const controller = { source: { kind: 'saved', playlistId: 'saved-1' }, name: 'Sesión', destination: { destinationId: 'destination-1', label: 'Subcrates' }, destinationDetected: false, detectionMissed: false, preview: null, receipt: null, pending: null, canPreview: true, canCommit: false, error: '', status: '', segmentSize: null, setName: (value) => calls.push(['name', value]), setSegmentSize: (value) => { calls.push(['split', value]); controller.segmentSize = value; }, chooseDestination: async () => calls.push(['choose']), requestPreview: async () => calls.push(['preview']), commit: async () => calls.push(['commit']), reveal: async () => calls.push(['reveal']) };
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
test('only the next available export step is primary and rendering never starts an operation', () => {
  const f = fixture(); const primary = () => all(f.root).filter(node => node.tagName === 'button' && /\bprimary\b/.test(node.className) && !node.hidden).map(node => node.id);
  try {
    const name = f.get('name'); f.controller.destination = null; f.controller.canPreview = false; f.render();
    assert.deepEqual(primary(), ['serato-export-choose']); assert.match(f.get('next-step').textContent, /1.*destino/i);
    f.controller.destination = { destinationId: 'chosen', label: '_Serato_' }; f.controller.canPreview = true; f.render();
    assert.deepEqual(primary(), ['serato-export-preview']); assert.match(f.get('next-step').textContent, /2.*previa/i); assert.match(f.get('choose').textContent, /Cambiar/);
    f.controller.preview = { filename: 'Set.crate', destinationLabel: '_Serato_', trackCount: 1, readiness: 'ready', warnings: [], blockers: [], backup: { required: false }, tracks: [{ title: 'One', artist: 'DJ' }] }; f.controller.canCommit = true; f.render();
    assert.deepEqual(primary(), ['serato-export-commit']); assert.match(f.get('next-step').textContent, /3.*confirm/i);
    f.controller.canCommit = false; f.controller.preview = { ...f.controller.preview, readiness: 'blocked', blockers: ['Archivo ausente'] }; f.render();
    assert.deepEqual(primary(), []); assert.match(f.get('next-step').textContent, /bloqueos/i); assert.match(text(f.get('proposal')), /Archivo ausente/);
    f.controller.preview = null; f.render(); assert.deepEqual(primary(), ['serato-export-preview']);
    f.controller.pending = 'preview'; f.render(); assert.deepEqual(primary(), []); assert.equal(f.get('name'), name); assert.deepEqual(f.calls, []);
  } finally { f.restore(); }
});
test('the page preview announces the parent crates the export will create', () => {
  const f = fixture(); try {
    const preview = { previewId: 'p', filename: 'XfinAudio%%Build 14-nov.crate', destinationLabel: 'Subcrates · Disco DJ', trackCount: 2, readiness: 'ready', warnings: [], blockers: [], canCommit: true, backup: { required: false }, parentsToCreate: ['XfinAudio'], tracks: [{ title: 'Uno', artist: 'A' }, { title: 'Dos', artist: 'B' }] };
    f.controller.preview = preview; f.controller.canCommit = true; f.render();
    assert.match(text(f.get('proposal')), /Se creará el crate «XfinAudio»/, 'one missing parent is announced before exporting');
    f.controller.preview = { ...preview, parentsToCreate: ['XfinAudio', 'XfinAudio%%Metadata'] }; f.render();
    assert.match(text(f.get('proposal')), /Se crearán los crates «XfinAudio», «XfinAudio › Metadata»/);
    f.controller.preview = { ...preview, parentsToCreate: [] }; f.render();
    assert.doesNotMatch(text(f.get('proposal')), /crates? «/, 'a preview without missing parents adds no line');
    f.controller.preview = { ...preview, parentsToCreate: undefined }; f.render();
    assert.doesNotMatch(text(f.get('proposal')), /crates? «/, 'a preview without the field renders exactly as before');
  } finally { f.restore(); }
});
test('a detected destination skips the required folder step and a miss explains itself', () => {
  const f = fixture(); const primary = () => all(f.root).filter(node => node.tagName === 'button' && /\bprimary\b/.test(node.className) && !node.hidden).map(node => node.id);
  try {
    f.controller.destinationDetected = true; f.render();
    assert.match(f.get('destination').textContent, /detectad[oa] automáticamente/i, 'a detection result must say it was automatic');
    assert.match(f.get('next-step').textContent, /2.*previa/i, 'a detected destination moves straight to the preview step');
    assert.deepEqual(primary(), ['serato-export-preview']); assert.match(f.get('choose').textContent, /Cambiar carpeta/);
    f.controller.destination = null; f.controller.destinationDetected = false; f.controller.detectionMissed = true; f.controller.canPreview = false; f.render();
    const notice = f.get('not-found'); assert.ok(notice, 'a miss must render an explanatory notice');
    assert.equal(notice.attrs.role, 'status'); assert.equal(notice.hidden, false);
    assert.match(notice.textContent, /no se encontró la carpeta _Serato_/i); assert.match(notice.textContent, /Abre Serato una vez/);
    assert.deepEqual(primary(), ['serato-export-choose']); assert.equal(f.get('choose').disabled, false); assert.match(f.get('next-step').textContent, /1.*destino/i);
    assert.deepEqual(f.calls, [], 'showing the miss must not start any operation');
    f.controller.destination = { destinationId: 'manual', label: '_Serato_' }; f.controller.detectionMissed = false; f.controller.canPreview = true; f.render();
    assert.equal(f.get('not-found').hidden, true, 'the notice disappears once a destination exists');
    assert.match(f.get('destination').textContent, /Destino seleccionado/);
  } finally { f.restore(); }
});

test('the options screen offers «Dividir en tramos» with today\'s single crate as the default (S1)', () => {
  const f = fixture(); try {
    const label = all(f.root).find((node) => node.tagName === 'label' && /Dividir en tramos/.test(node.textContent));
    assert.ok(label, 'the export options screen must offer the split control');
    assert.equal(label.attrs.for, 'serato-export-split');
    const split = f.get('split'); assert.ok(split, 'the split choice needs its own control');
    assert.deepEqual(split.children.filter((node) => node.tagName === 'option').map((node) => [node.value, node.textContent]),
      [['no', 'No dividir'], ['every', 'Cada N pistas']], 'the two choices are no split and every N tracks');
    assert.equal(split.value, 'no', 'no split is the default, exactly today\'s single crate');
    const size = f.get('split-size'); assert.ok(size, 'the tramo size needs its own number input');
    assert.equal(size.value, '5', 'five tracks per tramo by default');
    assert.equal(size.attrs.min, '2'); assert.equal(size.attrs.max, '50'); assert.equal(size.attrs['aria-invalid'], 'false');
    assert.equal(size.disabled, true, 'the size only matters with a split');
    assert.deepEqual(f.calls, [], 'rendering must never start an operation');
    split.value = 'every'; f.render();
    assert.equal(f.get('split-size').disabled, true, 'an unchanged controller state keeps the stored choice, not the typed one');
  } finally { f.restore(); }
});
test('the split choice sends only a whole number of 2 to 50 tracks and can be turned off again (S1)', () => {
  const f = fixture(); try {
    const split = f.get('split'), size = () => f.get('split-size');
    split.value = 'every'; split.dispatchEvent(new Event('change'));
    assert.deepEqual(f.calls, [['split', 5]], 'choosing a split starts from five tracks per tramo');
    f.render(); assert.equal(size().disabled, false); assert.equal(size().value, '5');
    for (const typed of ['7', '2', '50']) { size().value = typed; size().dispatchEvent(new Event('input')); }
    assert.deepEqual(f.calls, [['split', 5], ['split', 7], ['split', 2], ['split', 50]]);
    for (const typed of ['1', '51', '0', '-3', '2.5', '', 'abc']) {
      const count = f.calls.length; size().value = typed; size().dispatchEvent(new Event('input'));
      assert.equal(f.calls.length, count, `${typed} is not a valid tramo`);
      assert.equal(size().attrs['aria-invalid'], 'true', `${typed} must be visibly refused`);
    }
    split.value = 'no'; split.dispatchEvent(new Event('change'));
    assert.deepEqual(f.calls.at(-1), ['split', null], 'no dividir clears the split for this export');
    f.render(); assert.equal(size().disabled, true);
  } finally { f.restore(); }
});
test('the preview lists every crate of the tree with its count, parent first and children indented (S4)', () => {
  const f = fixture(); try {
    const parent = 'XfinAudio%%Harmonic Journey 14-nov.crate';
    f.controller.preview = { previewId: 'p', filename: parent, destinationLabel: 'Subcrates', trackCount: 20, readiness: 'ready', warnings: [], blockers: [], canCommit: true, backup: { required: false }, parentsToCreate: ['XfinAudio'], tracks: [{ title: 'Uno', artist: 'A' }], crates: [
      { name: parent, trackCount: 20, action: 'create' },
      { name: 'XfinAudio%%Harmonic Journey 14-nov%%1 (1-5).crate', trackCount: 5, action: 'create' },
      { name: 'XfinAudio%%Harmonic Journey 14-nov%%4 (16-20).crate', trackCount: 5, action: 'replace' },
    ] }; f.controller.canCommit = true; f.render();
    const list = f.get('crates'); assert.ok(list, 'a split preview must list the whole tree');
    assert.deepEqual(list.children.map((node) => node.textContent), [
      '«XfinAudio › Harmonic Journey 14-nov» · 20 pistas · se crea',
      '«XfinAudio › Harmonic Journey 14-nov › 1 (1-5)» · 5 pistas · se crea',
      '«XfinAudio › Harmonic Journey 14-nov › 4 (16-20)» · 5 pistas · se reemplaza',
    ], 'the parent comes first and every crate carries its own count and action');
    assert.match(list.children[0].className, /crate-parent/); assert.doesNotMatch(list.children[0].className, /crate-child/);
    for (const node of list.children.slice(1)) { assert.match(node.className, /crate-child/); assert.doesNotMatch(node.className, /crate-parent/); }
    assert.match(text(f.get('proposal')), /Se escribirán 3 crates/);
    f.controller.preview = { ...f.controller.preview, crates: undefined }; f.render();
    assert.equal(f.get('proposal').children.some((node) => node.id === 'serato-export-crates'), false, 'without a split the preview reads exactly as before');
    assert.doesNotMatch(text(f.get('proposal')), /Se escribirán|crates:/);
    f.controller.preview = { previewId: 'single', filename: 'Set.crate', destinationLabel: 'Subcrates', trackCount: 2, readiness: 'ready', warnings: [], blockers: [], canCommit: true, backup: { required: false }, tracks: [{ title: 'Uno', artist: 'A' }], crates: [] }; f.render();
    assert.doesNotMatch(text(f.get('proposal')), /Se escribirán/, 'an empty crate list adds nothing');
  } finally { f.restore(); }
});
test('a tree receipt says how many crates were written and names each one (S6)', () => {
  const f = fixture(); try {
    f.controller.receipt = { receiptId: 'r', filename: 'XfinAudio%%Sesión 14-nov.crate', destinationLabel: 'Subcrates', trackCount: 12, validated: true, backupCreated: true, parentsCreated: ['XfinAudio'], files: [
      { name: 'XfinAudio%%Sesión 14-nov.crate', trackCount: 12 },
      { name: 'XfinAudio%%Sesión 14-nov%%1 (1-5).crate', trackCount: 5 },
      { name: 'XfinAudio%%Sesión 14-nov%%3 (11-12).crate', trackCount: 2 },
    ] }; f.render();
    const receipt = f.get('receipt');
    assert.match(text(receipt), /Crates escritos: 3/); assert.match(text(receipt), /Crate validado tras la escritura/);
    const written = all(receipt).find((node) => node.id === 'serato-export-receipt-crates');
    assert.ok(written, 'the receipt must name every crate it wrote');
    assert.deepEqual(written.children.map((node) => node.textContent), [
      '«XfinAudio › Sesión 14-nov» · 12 pistas',
      '«XfinAudio › Sesión 14-nov › 1 (1-5)» · 5 pistas',
      '«XfinAudio › Sesión 14-nov › 3 (11-12)» · 2 pistas',
    ]);
    assert.match(text(receipt), /crate padre/, 'the page says what «Mostrar crate exportado» opens');
    assert.equal(f.get('reveal').disabled, false);
    f.controller.receipt = { receiptId: 's', filename: 'Set.crate', destinationLabel: 'Subcrates', trackCount: 2, validated: true, backupCreated: false }; f.render();
    assert.doesNotMatch(text(f.get('receipt')), /Crates escritos/, 'a single crate receipt reads exactly as before');
    assert.equal(all(f.get('receipt')).some((node) => node.id === 'serato-export-receipt-crates'), false);
  } finally { f.restore(); }
});

test('a metadata worklist export offers no split, because the core refuses one with it', () => {
  const f = fixture(); try {
    f.controller.source = { kind: 'metadata', status: 'complete', missingField: null, trackIds: ['a'.repeat(64)] }; f.render();
    assert.equal(f.get('split').disabled, true, 'a worklist is not a set, so it is not split into tramos');
    assert.equal(f.get('split-size').disabled, true);
    f.controller.segmentSize = 5; f.render(); assert.equal(f.get('split').disabled, true);
    assert.deepEqual(f.calls, [], 'showing a worklist never changes the split by itself');
  } finally { f.restore(); }
});
