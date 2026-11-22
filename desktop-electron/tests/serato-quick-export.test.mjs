import assert from 'node:assert/strict';
import test from 'node:test';
import { SeratoQuickExportController, createSeratoQuickExportView } from '../.out/renderer/serato-quick-export.js';
const source = { kind: 'review', reviewId: 'review-1' };
const destination = { destinationId: 'destination-1', label: '_Serato_ · dd' };
const receipt = { receiptId: 'receipt-1', filename: 'Mi sesión.crate', destinationLabel: '_Serato_ · dd', trackCount: 2, validated: true, backupCreated: false };
const exported = { status: 'exported', receipt };
function fixture(overrides = {}) {
  const calls = []; let busy = false;
  const api = {
    quickSeratoExport: async (input) => { calls.push(['export', input]); return exported; },
    chooseSeratoDestination: async () => { calls.push(['choose']); return destination; },
    revealSeratoExport: async (input) => { calls.push(['reveal', input]); },
    ...overrides,
  };
  const controller = new SeratoQuickExportController(api, {
    canAct: () => !busy, changed: () => {},
    perform: async (_label, task, apply, failure) => { if (busy) return; busy = true; try { apply(await task(), true); } catch (error) { failure(error); } finally { busy = false; } },
  });
  return { controller, calls };
}
test('one action sends only the scoped source and the crate name and reports the receipt in Spanish', async () => {
  const f = fixture(); await f.controller.export(source, 'Mi sesión');
  assert.deepEqual(f.calls, [['export', { source, name: 'Mi sesión' }]]);
  assert.equal(f.controller.notice, 'Crate «Mi sesión» exportado a Serato');
  assert.match(f.controller.detail, /Mi sesión\.crate/);
  assert.match(f.controller.detail, /2 pistas/);
  assert.deepEqual(f.controller.receipt, receipt);
  assert.equal(f.controller.needsDestination, false);
  assert.deepEqual(f.controller.blockers, []);
  assert.equal(f.controller.tone, 'success');
});
test('a blocked preview shows the blockers and never reports a receipt', async () => {
  const blocker = 'Review sources or settings changed; generate a new review';
  const f = fixture({ quickSeratoExport: async () => ({ status: 'blocked', filename: 'Mi sesión.crate', blockers: [blocker] }) });
  await f.controller.export(source, 'Mi sesión');
  assert.match(f.controller.notice, /^No se exportó nada/);
  assert.equal(f.controller.detail, 'Bloqueos que impiden exportar:');
  assert.deepEqual(f.controller.blockers, [blocker]);
  assert.equal(f.controller.receipt, null);
  assert.equal(f.controller.needsDestination, false);
});
test('a missing destination offers the manual choice and then continues to the same confirmation', async () => {
  const sent = []; let step = 0;
  const f = fixture({ quickSeratoExport: async (input) => { sent.push(input); step += 1; return step === 1 ? { status: 'needs_destination' } : exported; } });
  await f.controller.export(source, 'Mi sesión');
  assert.equal(f.controller.needsDestination, true);
  assert.equal(f.controller.notice, 'No se encontró la carpeta _Serato_ de destino');
  assert.match(f.controller.detail, /Abre Serato una vez/);
  assert.equal(f.controller.receipt, null);
  await f.controller.chooseDestination();
  assert.deepEqual(f.calls, [['choose']]);
  assert.deepEqual(sent, [{ source, name: 'Mi sesión' }, { source, name: 'Mi sesión' }]);
  assert.equal(f.controller.needsDestination, false);
  assert.deepEqual(f.controller.receipt, receipt);
});
test('a cancelled native dialog says nothing was written and never reports a receipt', async () => {
  const sent = []; const f = fixture({ quickSeratoExport: async (input) => { sent.push(input); return { status: 'cancelled' }; } });
  await f.controller.export(source, 'Mi sesión');
  assert.equal(f.controller.notice, 'Exportación cancelada');
  assert.equal(f.controller.detail, 'No se escribió nada.');
  assert.equal(f.controller.tone, 'quiet');
  assert.equal(f.controller.receipt, null);
  assert.deepEqual(sent, [{ source, name: 'Mi sesión' }]);
});
test('reveal needs a receipt and a pending export refuses repeats', async () => {
  const f = fixture(); await f.controller.reveal(); assert.deepEqual(f.calls, []);
  await f.controller.export(source, 'Mi sesión'); await f.controller.reveal();
  assert.deepEqual(f.calls.at(-1), ['reveal', { receiptId: 'receipt-1' }]);
  let finish; const sent = [];
  const g = fixture({ quickSeratoExport: (input) => { sent.push(input); return new Promise((resolve) => { finish = resolve; }); } });
  const running = g.controller.export(source, 'Mi sesión');
  await g.controller.export(source, 'Otra');
  await g.controller.chooseDestination();
  assert.equal(sent.length, 1, 'a pending export is never repeated');
  assert.equal(g.controller.pending, 'export');
  finish(exported); await running;
  assert.equal(g.controller.pending, null);
  assert.deepEqual(g.controller.receipt, receipt);
});
class Element extends EventTarget {
  constructor(tag = 'div') { super(); this.tagName = tag; }
  children = []; attrs = {}; dataset = {}; textContent = ''; value = ''; disabled = false; hidden = false; classes = new Set(); id = '';
  className = '';
  classList = { toggle: (key, active) => active ? this.classes.add(key) : this.classes.delete(key), contains: (key) => this.classes.has(key) };
  setAttribute(key, value) { this.attrs[key] = String(value); }
  removeAttribute(key) { delete this.attrs[key]; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  set innerHTML(_) { throw new Error('Unsafe HTML'); }
}
const all = (node) => [node, ...node.children.flatMap(all)];
const text = (node) => [node.textContent, ...node.children.map(text)].join(' ');
function view() {
  const previous = globalThis.document; globalThis.document = { createElement: (tag) => new Element(tag) };
  const root = new Element(); const calls = []; let available = true;
  const controller = { request: { source, name: 'Mi sesión' }, notice: '', detail: '', tone: 'quiet', blockers: [], receipt: null, needsDestination: false, pending: null, reveal: async () => calls.push(['reveal']), chooseDestination: async () => calls.push(['choose']) };
  const render = createSeratoQuickExportView(root, controller, { canAct: () => available }, (given, name) => calls.push(['advanced', given, name])); render();
  return { root, controller, calls, render, get: (id) => all(root).find((node) => node.id === id), block: () => { available = false; render(); }, restore: () => { globalThis.document = previous; } };
}
test('the quick notice shows the Spanish result with reveal, folder choice and the advanced page link', () => {
  const f = view(); try {
    f.controller.notice = 'Crate «Mi sesión» exportado a Serato'; f.controller.detail = 'Mi sesión.crate · _Serato_ · dd · 2 pistas'; f.controller.receipt = receipt; f.controller.tone = 'success'; f.render();
    const section = f.get('serato-quick-export');
    assert.equal(section.hidden, false); assert.equal(section.attrs.role, 'status'); assert.equal(section.attrs['aria-live'], 'polite');
    assert.equal(f.get('serato-quick-export-notice').textContent, 'Crate «Mi sesión» exportado a Serato');
    assert.match(f.get('serato-quick-export-detail').textContent, /2 pistas/);
    const reveal = f.get('serato-quick-export-reveal');
    assert.equal(reveal.hidden, false); assert.equal(reveal.textContent, 'Mostrar en Finder');
    assert.equal(f.get('serato-quick-export-choose').hidden, true);
    assert.equal(f.get('serato-quick-export-advanced').textContent, 'Opciones de exportación');
    reveal.dispatchEvent(new Event('click')); f.get('serato-quick-export-advanced').dispatchEvent(new Event('click'));
    assert.deepEqual(f.calls, [['reveal'], ['advanced', source, 'Mi sesión']]);
    f.block(); assert.equal(reveal.disabled, true); assert.equal(f.get('serato-quick-export-advanced').disabled, true);
    assert.ok(!all(f.root).some((node) => ['script', 'img'].includes(node.tagName)));
  } finally { f.restore(); }
});
test('the notice offers the folder choice on a miss and lists the blockers on a block', () => {
  const f = view(); try {
    f.controller.notice = 'No se encontró la carpeta _Serato_ de destino'; f.controller.detail = 'Abre Serato una vez con ese disco conectado para crearla; después podrás elegir la carpeta manualmente.'; f.controller.needsDestination = true; f.controller.tone = 'blocked'; f.render();
    const section = f.get('serato-quick-export');
    assert.equal(section.classes.has('is-error'), true);
    const choose = f.get('serato-quick-export-choose');
    assert.equal(choose.hidden, false); assert.equal(choose.textContent, 'Elegir carpeta');
    choose.dispatchEvent(new Event('click')); assert.deepEqual(f.calls, [['choose']]);
    f.controller.notice = 'No se exportó nada: la selección no está lista'; f.controller.detail = 'Bloqueos que impiden exportar:'; f.controller.needsDestination = false; f.controller.blockers = ['Archivo ausente', 'Otra pista ausente']; f.render();
    assert.equal(f.get('serato-quick-export-choose').hidden, true);
    assert.equal(f.get('serato-quick-export-reveal').hidden, true);
    assert.deepEqual(f.get('serato-quick-export-blockers').children.map((node) => node.textContent), ['Archivo ausente', 'Otra pista ausente']);
    assert.match(text(f.root), /Bloqueos que impiden exportar/);
    f.controller.notice = ''; f.controller.detail = ''; f.controller.blockers = []; f.render();
    assert.equal(f.get('serato-quick-export').hidden, true, 'an empty state must not leave a stale notice');
  } finally { f.restore(); }
});

test('a core stop drops a stale notice and receipt but keeps the request for the same export',async()=>{
 const f=fixture();await f.controller.export(source,'Mi sesión');
 assert.deepEqual(f.controller.receipt,receipt);assert.match(f.controller.notice,/exportado a Serato/);
 f.controller.forgetCore();
 assert.equal(f.controller.receipt,null);assert.equal(f.controller.notice,'');assert.equal(f.controller.detail,'');
 assert.equal(f.controller.needsDestination,false);assert.deepEqual(f.controller.blockers,[]);assert.equal(f.controller.tone,'quiet');
 assert.deepEqual(f.controller.request,{source,name:'Mi sesión'});
 await f.controller.export(source,'Mi sesión');
 assert.deepEqual(f.calls.filter(([operation])=>operation==='export').length,2,'the button exports again through the fresh core');
 assert.deepEqual(f.controller.receipt,receipt);
});
test('a generated set exports without a crate name and reports the name the core chose', async () => {
  const sent = [];
  const f = fixture({ quickSeratoExport: async (input) => { sent.push(['export', input]); return { status: 'exported', receipt: { ...receipt, filename: 'XfinAudio%%Build 6-jun.crate' } }; } });
  await f.controller.export(source, '');
  assert.deepEqual(sent, [['export', { source }]], 'no name travels for a generated set');
  assert.equal(f.controller.notice, 'Crate «XfinAudio%%Build 6-jun» exportado a Serato');
  assert.match(f.controller.detail, /XfinAudio%%Build 6-jun\.crate · _Serato_ · dd · 2 pistas/);
});
test('a saved playlist keeps exporting its own name unchanged', async () => {
  const f = fixture(); await f.controller.export({ kind: 'saved', playlistId: '1' }, 'Sesión guardada');
  assert.deepEqual(f.calls, [['export', { source: { kind: 'saved', playlistId: '1' }, name: 'Sesión guardada' }]]);
});

test('a quick export mentions the parent crate briefly and says nothing extra otherwise', async () => {
  const f = fixture({ quickSeratoExport: async () => ({ status: 'exported', receipt: { ...receipt, filename: 'XfinAudio%%Build 14-nov.crate', parentsCreated: ['XfinAudio'] } }) });
  await f.controller.export(source, '');
  assert.equal(f.controller.notice, 'Crate «XfinAudio%%Build 14-nov» exportado a Serato');
  assert.equal(f.controller.detail, 'XfinAudio%%Build 14-nov.crate · _Serato_ · dd · 2 pistas · Crate padre «XfinAudio» creado');
  const g = fixture({ quickSeratoExport: async () => ({ status: 'exported', receipt: { ...receipt, filename: 'XfinAudio%%Metadata%%Pendientes.crate', parentsCreated: ['XfinAudio', 'XfinAudio%%Metadata'] } }) });
  await g.controller.export(source, '');
  assert.equal(g.controller.detail, 'XfinAudio%%Metadata%%Pendientes.crate · _Serato_ · dd · 2 pistas · Crates padre creados: «XfinAudio», «XfinAudio › Metadata»');
  const h = fixture(); await h.controller.export(source, 'Mi sesión');
  assert.equal(h.controller.detail, 'Mi sesión.crate · _Serato_ · dd · 2 pistas', 'a receipt without created parents reads exactly as before');
});
test('a refused export request still says next to the button that it did not start (S2)', async () => {
  const refused = "Error invoking remote method 'xfin:action': [invalid_source] Invalid export source";
  const f = fixture({ quickSeratoExport: async () => { throw new Error(refused); } });
  await f.controller.export({ kind: 'saved', playlistId: '1' }, 'Mi sesión');
  assert.equal(f.controller.tone, 'blocked');
  assert.equal(f.controller.notice, 'No se pudo iniciar la exportación a Serato');
  assert.equal(f.controller.detail, 'La selección no está disponible para esta exportación. Vuelve a abrirla y revisar sus pistas.');
  assert.equal(f.controller.receipt, null);
  assert.deepEqual(f.controller.request, { source: { kind: 'saved', playlistId: '1' }, name: 'Mi sesión' }, 'the request survives so the button can be retried');
});
test('an uncoded refusal answers in Spanish too, never only the generic bar (S2)', async () => {
  const f = fixture({ quickSeratoExport: async () => { throw new Error('Invalid export source'); } });
  await f.controller.export(source, 'Mi sesión');
  assert.equal(f.controller.tone, 'blocked');
  assert.equal(f.controller.notice, 'No se pudo iniciar la exportación a Serato');
  assert.equal(f.controller.detail, 'No se pudo completar la operación. Actualiza la información y vuelve a intentarlo.');
  assert.equal(f.controller.receipt, null);
});
test('a failed reveal keeps its own answer and never claims the export did not start', async () => {
  const f = fixture({ revealSeratoExport: async () => { throw new Error('[invalid_preview] Receipt not found'); } });
  await f.controller.export(source, 'Mi sesión');
  assert.deepEqual(f.controller.receipt, receipt);
  await f.controller.reveal();
  assert.equal(f.controller.notice, '');
  assert.equal(f.controller.tone, 'quiet');
});
test('an export refused because Serato DJ is open says so next to the button and nothing was written (S13)', async () => {
  let open = true;
  const f = fixture({ quickSeratoExport: async (input) => { f.calls.push(['export', input]); if (open) throw new Error("Error invoking remote method 'xfin:action': [serato_running] Close Serato DJ"); return exported; } });
  await f.controller.export(source, 'Mi sesión');
  assert.equal(f.controller.notice, 'Serato DJ está abierto');
  assert.equal(f.controller.detail, 'Cierra Serato DJ antes de exportar. Si Serato está abierto, al cerrarse borra los crates nuevos. Ciérralo y vuelve a confirmar.');
  assert.equal(f.controller.tone, 'blocked'); assert.equal(f.controller.receipt, null);
  open = false; await f.controller.export(source, 'Mi sesión');
  assert.equal(f.controller.tone, 'success'); assert.deepEqual(f.controller.receipt, receipt);
});

test('a one-click export never carries a split, so it writes today\'s single crate (S1)', async () => {
  const f = fixture(); await f.controller.export(source, 'Mi sesión');
  assert.deepEqual(f.calls, [['export', { source, name: 'Mi sesión' }]], 'the quick export asks for no tramo at all');
  assert.equal(f.controller.notice, 'Crate «Mi sesión» exportado a Serato');
  assert.equal(f.controller.detail, 'Mi sesión.crate · _Serato_ · dd · 2 pistas', 'the single-crate receipt reads exactly as before');
});
