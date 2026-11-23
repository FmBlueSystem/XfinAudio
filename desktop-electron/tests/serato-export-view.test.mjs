import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
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
  const controller = { source: { kind: 'saved', playlistId: 'saved-1' }, name: 'Sesión', destination: { destinationId: 'destination-1', label: 'Subcrates' }, destinationDetected: false, detectionMissed: false, preview: null, receipt: null, pending: null, canPreview: true, canCommit: false, error: '', status: '', segmentSize: null, splitMode: 'none', setName: (value) => calls.push(['name', value]), setSegmentSize: (value) => { calls.push(['split', value]); controller.segmentSize = value; controller.splitMode = value === null ? 'none' : 'every'; }, setSplitMode: (value) => { calls.push(['mode', value]); controller.splitMode = value; }, chooseDestination: async () => calls.push(['choose']), requestPreview: async () => calls.push(['preview']), commit: async () => calls.push(['commit']), reveal: async () => calls.push(['reveal']) };
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
      [['no', 'No dividir'], ['every', 'Cada N pistas'], ['phases', 'Por fases de energía']], 'the three choices are no split, every N tracks and the set\'s own energy phases');
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
test('«Por fases de energía» disables the tramo size and explains what the phases are (S4)', () => {
  const f = fixture(); try {
    const split = f.get('split'), size = () => f.get('split-size');
    assert.match(f.get('split-hint').textContent, /Por fases de energía/, 'the hint must explain the third choice');
    assert.match(f.get('split-hint').textContent, /Apertura/, 'the hint names the phases the core writes');
    assert.match(f.get('split-hint').textContent, /8 pistas/, 'the hint states the minimum the core really splits');
    split.value = 'phases'; split.dispatchEvent(new Event('change'));
    assert.deepEqual(f.calls, [['mode', 'phases']], 'phases are their own choice, never a tramo size');
    f.render();
    assert.equal(split.value, 'phases', 'the control shows the phase choice');
    assert.equal(size().disabled, true, 'the phase split has no fixed number of tracks');
    f.controller.segmentSize = 5; f.render();
    assert.equal(split.value, 'phases'); assert.equal(size().disabled, true, 'a remembered tramo size cannot enable the input in phases mode');
    split.value = 'every'; split.dispatchEvent(new Event('change'));
    assert.deepEqual(f.calls.at(-1), ['split', 5], 'changing back to every N tracks keeps the size it had');
  } finally { f.restore(); }
});
test('«Pistas por tramo» is disabled for «Sin dividir» and «Por fases de energía», enabled for «Cada N pistas», and keeps the number typed (S1)', () => {
  const f = fixture(); try {
    const split = f.get('split'), size = () => f.get('split-size');
    const label = all(f.root).find((node) => node.tagName === 'label' && node.textContent === 'Pistas por tramo');
    assert.ok(label, 'the size keeps its own label, so assistive tech reads which field is disabled');
    assert.equal(label.attrs.for, 'serato-export-split-size');
    assert.match(f.get('split-hint').textContent, /vale solo para esta exportación/, 'the help text still says the choice only applies to this export');
    assert.equal(split.value, 'no'); assert.equal(size().disabled, true, '«Sin dividir» has no tramo size');
    split.value = 'phases'; split.dispatchEvent(new Event('change')); f.render();
    assert.equal(size().disabled, true, '«Por fases de energía» decides its own runs: the size cannot be edited');
    assert.equal(size().hidden, false, 'the field stays in place, announced as disabled instead of disappearing');
    split.value = 'no'; split.dispatchEvent(new Event('change')); f.render();
    assert.equal(size().disabled, true, '«Sin dividir» disables it again');
    split.value = 'every'; split.dispatchEvent(new Event('change')); f.render();
    assert.equal(size().disabled, false, '«Cada N pistas» is the only choice with a number');
    size().value = '12'; size().dispatchEvent(new Event('input')); f.render();
    assert.equal(size().value, '12');
    split.value = 'phases'; split.dispatchEvent(new Event('change')); f.render();
    assert.equal(size().disabled, true); assert.equal(size().value, '12', 'the number typed earlier survives the phase choice');
    split.value = 'every'; split.dispatchEvent(new Event('change')); f.render();
    assert.equal(size().disabled, false); assert.equal(size().value, '12', 're-enabling shows the same number, not the default');
    assert.deepEqual(f.calls.at(-1), ['split', 12], 'the kept number is what the export sends');
  } finally { f.restore(); }
});
test('the disabled «Pistas por tramo» field also looks disabled in the dark theme (S1)', async () => {
  const css = await readFile(new URL('../renderer/styles.css', import.meta.url), 'utf8');
  const rule = /#serato-export-split-size:disabled\s*\{([^}]*)\}/.exec(css);
  assert.ok(rule, 'author input colours beat the browser default, so the field must be styled disabled or it still looks editable');
  assert.match(rule[1], /color:\s*#6d7885/, 'a disabled field uses the muted text colour the app already uses for disabled buttons');
  assert.match(rule[1], /background:\s*#101216/);
  assert.match(rule[1], /cursor:\s*not-allowed/);
});
test('a phases preview lists its phase crates like segments and explains a set it cannot split (S4, S5)', () => {
  const f = fixture(); try {
    const parent = 'XfinAudio%%Sesión 14-nov.crate';
    const base = { previewId: 'p', filename: parent, destinationLabel: 'Subcrates', trackCount: 12, readiness: 'ready', warnings: [], blockers: [], canCommit: true, backup: { required: false }, parentsToCreate: ['XfinAudio'], tracks: [{ title: 'Uno', artist: 'A' }] };
    f.controller.preview = { ...base, crates: [
      { name: parent, trackCount: 12, action: 'create' },
      { name: 'XfinAudio%%Sesión 14-nov%%1 Apertura (1-2).crate', trackCount: 2, action: 'create' },
      { name: 'XfinAudio%%Sesión 14-nov%%4 Cierre (11-12).crate', trackCount: 2, action: 'replace' },
    ] }; f.render();
    const list = f.get('crates'); assert.ok(list, 'a phase tree is listed exactly like a segment tree');
    assert.deepEqual(list.children.map((node) => node.textContent), [
      '«XfinAudio › Sesión 14-nov» · 12 pistas · se crea',
      '«XfinAudio › Sesión 14-nov › 1 Apertura (1-2)» · 2 pistas · se crea',
      '«XfinAudio › Sesión 14-nov › 4 Cierre (11-12)» · 2 pistas · se reemplaza',
    ]);
    const messages = {
      too_few_tracks: 'La lista es muy corta para dividirla por fases (mínimo 8 pistas); se exportará sin dividir.',
      too_few_energies: 'Faltan datos de energía en la lista; se exportará sin dividir.',
      flat: 'La energía de la lista es casi pareja; no hay fases claras y se exportará sin dividir.',
      single_phase: 'La energía de la lista forma una sola fase; se exportará sin dividir.',
    };
    for (const [reason, message] of Object.entries(messages)) {
      f.controller.preview = { ...base, phaseReason: reason }; f.render();
      assert.ok(text(f.get('proposal')).includes(message), `${reason} must be explained in that exact Spanish sentence`);
      assert.equal(f.get('proposal').children.some((node) => node.id === 'serato-export-crates'), false, 'the parent alone lists no phase crates');
    }
    f.controller.preview = { ...base }; f.render();
    assert.doesNotMatch(text(f.get('proposal')), /sin dividir/, 'a preview without a reason adds no line');
    f.controller.preview = { ...base, phaseReason: 'unknown_from_a_newer_core' }; f.render();
    assert.doesNotMatch(text(f.get('proposal')), /sin dividir/, 'a reason this screen does not know is never invented');
  } finally { f.restore(); }
});
