import assert from 'node:assert/strict';
import test from 'node:test';
import { LoudnessController } from '../.out/renderer/loudness.js';
import { createLoudnessView } from '../.out/renderer/loudness-view.js';
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
const track = (n) => ({ id: n.toString(16).padStart(64, '0'), title: n === 1 ? '<img src=x>' : `Pista ${n}`, artist: 'DJ', bpm: null, key: null, energy: null, duration: 120 });
const item = (n) => ({ track: track(n), state: 'unmeasured', complete: false, lufs: null, lra: null, truePeak: null });
async function fixture(patch = {}, total = 6, apiExtras = {}) {
  const previous = globalThis.document; globalThis.document = { createElement: (tag) => new Element(tag) }; let available = true; const calls = []; const root = new Element();
  const tracks = Array.from({ length: total }, (_, n) => item(n + 1));
  const snapshot = { revision: 'a'.repeat(64), enabled: true, targetLufs: -10, toleranceLu: 2, available: true, reason: 'ready', totalTracks: total, tracks, ...patch };
  let render = () => {};
  const controller = new LoudnessController({ getLoudnessStatus: async () => snapshot, saveLoudnessSettings: async (input) => { calls.push(['save', input]); return { ...snapshot, ...input }; }, previewLoudness: async (input) => { calls.push(['preview', input]); return { previewId: '12345678-1234-4123-8123-123456789012', trackCount: input.trackIds.length, backupBytes: 4096, force: input.force, replaceComments: true, tracks: input.trackIds.map((id) => tracks.find((entry) => entry.track.id === id).track) }; }, runLoudness: async (input) => { calls.push(['run', input]); return { cancelled: true, changedCount: 1, unchangedCount: 0, failureCount: 1, backupCount: 2, status: snapshot }; }, ...apiExtras }, { canAct: () => available, changed: () => render(), dirtyChanged: () => {}, applied: () => {}, perform: async (_label, task, apply, fail) => { try { apply(await task(), true); } catch (error) { fail(error); } } });
  render = createLoudnessView(root, controller, { canAct: () => available }); await controller.load(); render();
  return { root, controller, calls, snapshot, tracks, render, get: (id) => all(root).find((node) => node.id === `loudness-${id}`), block: () => { available = false; render(); }, restore: () => { globalThis.document = previous; } };
}
test('single enabled setting has explicit replacement warning and original bounds, stable accessible inputs', async () => {
  const f = await fixture(); try {
    for (const caption of ['automática', 'comentarios', '−30', 'LUFS', 'tolerancia', 'preescucha']) assert.ok(text(f.root).toLowerCase().includes(caption.toLowerCase()), caption);
    const enabled = f.get('enabled'); assert.equal(enabled.type, 'checkbox'); assert.equal(f.get('target').min, '-30'); assert.equal(f.get('target').max, '0'); assert.equal(f.get('tolerance').max, '10'); for (const id of ['enabled', 'target', 'tolerance']) assert.ok(all(f.root).some((node) => node.tagName === 'label' && node.attrs.for === `loudness-${id}`));
    const target = f.get('target'); f.render(); assert.equal(f.get('target'), target); target.value = '-14'; target.dispatchEvent(new Event('change')); assert.equal(f.controller.snapshot.targetLufs, -14); assert.equal(f.calls.length, 0); assert.equal(f.get('preview').disabled, true); assert.ok(!all(f.root).some((node) => node.tagName === 'audio' || node.tagName === 'img')); assert.ok(text(f.root).includes('<img src=x>'));
  } finally { f.restore(); }
});
test('truthful complete, partial and failure measurements preserve numeric distinctions and peak warnings', async () => {
  const metrics = [
    { state: 'measured', complete: true, lufs: -9.2, lra: 4.5, truePeak: 0 },
    { state: 'too_short', complete: false, lufs: -13.4, lra: null, truePeak: -0.4 },
    { state: 'unmeasurable', complete: false, lufs: null, lra: null, truePeak: null },
    { state: 'transient_failure', complete: false, lufs: null, lra: null, truePeak: null },
    { state: 'unsupported', complete: false, lufs: null, lra: null, truePeak: null },
    { state: 'measured', complete: false, lufs: -11, lra: null, truePeak: null },
  ];
  const f = await fixture({ tracks: metrics.map((fields, n) => ({ ...item(n + 1), ...fields })) }); try {
    for (const expected of ['−9.2', '4.5', '0.0', '−13.4', '−0.4', 'recorte', 'Poco margen', '60 s', 'No medible', 'Fallo temporal', 'No compatible', 'incompleta']) assert.ok(text(f.root).includes(expected), expected);
    const rows = f.get('rows').children; assert.equal(rows[0].children[3].textContent, '−9.2'); assert.equal(rows[1].children[4].textContent, 'No estable (<60 s)'); assert.equal(rows[5].children[3].textContent, '—');
  } finally { f.restore(); }
});
test('selection and preview each paginate100 without hiding scope; preview never calls run', async () => {
  const f = await fixture({}, 201); try {
    assert.equal(f.get('rows').children.length, 100); f.get('select-page').dispatchEvent(new Event('click')); assert.equal(f.controller.selectedIds.length, 100); f.get('next').dispatchEvent(new Event('click')); assert.equal(f.controller.page, 1); f.get('select-page').dispatchEvent(new Event('click')); assert.equal(f.controller.selectedIds.length, 200); await f.controller.requestPreview(); assert.equal(f.get('preview-tracks').children.length, 100); assert.match(text(f.get('preview-section')), /200 pistas/); f.get('preview-next').dispatchEvent(new Event('click')); assert.equal(f.get('preview-tracks').children.length, 100); assert.ok(text(f.get('preview-tracks')).includes('Pista 200')); assert.equal(f.calls.filter(([kind]) => kind === 'run').length, 0); assert.match(text(f.get('preview-section')), /4096 bytes/); assert.match(text(f.get('preview-section')), /diálogo del sistema/);
  } finally { f.restore(); }
});
test('single-track reanalysis offers preview, and run result reports cancellation and completed writes truthfully', async () => {
  const f = await fixture(); try {
    const reanalyze = all(f.get('rows')).find((node) => node.tagName === 'button'); reanalyze.dispatchEvent(new Event('click')); await new Promise((resolve) => setImmediate(resolve)); assert.deepEqual(f.calls.at(-1), ['preview', { trackIds: [track(1).id], force: true }]); assert.match(text(f.get('preview-section')), /Reanálisis/); f.controller.setSelection([track(1).id, track(2).id]); await f.controller.requestPreview(); await f.controller.run(); assert.match(text(f.get('result')), /cancelada/i); for (const expected of ['1 escrituras completadas', '1 fallidas', '2 copias']) assert.ok(text(f.get('result')).includes(expected), expected); assert.equal(f.controller.preview, null);
  } finally { f.restore(); }
});
test('offline and pending disable every action, stale status remains marked, and missing engine explains unavailability', async () => {
  const f = await fixture(); try {
    f.controller.setTarget(-12); f.controller.invalidateContext(); f.block(); assert.match(text(f.root), /desactualizados/i); assert.match(text(f.root), /sin guardar/); for (const node of all(f.root).filter((node) => ['input', 'button'].includes(node.tagName))) assert.equal(node.disabled, true, node.id); assert.equal(f.get('error').attrs.role, 'alert');
  } finally { f.restore(); }
  const g = await fixture({ available: false, reason: 'missing_engine' }); try { assert.match(text(g.get('availability')), /no está instalado/i); assert.equal(g.get('preview').disabled, true); } finally { g.restore(); }
});
test('post-write receipt warning is prominent and remains separate from the mutation counts', async () => {
  const f = await fixture(); try { f.controller.result = { cancelled: false, changedCount: 1, unchangedCount: 0, failureCount: 0, backupCount: 1, status: f.snapshot, warning: 'Conserva las copias y actualiza antes de continuar.' }; f.render(); assert.equal(f.get('result-warning').attrs.role, 'alert'); assert.equal(f.get('result-warning').hidden, false); assert.match(f.get('result-warning').textContent, /Conserva las copias/); assert.match(f.get('result').textContent, /1 escrituras completadas.*1 copias/); } finally { f.restore(); }
});
test('backup reveal has an accessible disabled fallback and reports no-backup guidance without writing', async () => {
  const missing = await fixture(); try { assert.equal(missing.get('reveal-backups').textContent, 'Mostrar copias de seguridad'); assert.equal(missing.get('reveal-backups').disabled, true); } finally { missing.restore(); }
  let requests = 0; const f = await fixture({}, 6, { revealLoudnessBackups: async (...args) => { assert.deepEqual(args, []); requests++; return { found: false }; } }); try { assert.equal(f.get('reveal-backups').disabled, false); f.get('reveal-backups').dispatchEvent(new Event('click')); await new Promise((resolve) => setImmediate(resolve)); assert.equal(requests, 1); assert.equal(f.get('backup-notice').attrs.role, 'status'); assert.match(f.get('backup-notice').textContent, /Todavía no hay copias/); assert.equal(f.calls.length, 0); f.block(); assert.equal(f.get('reveal-backups').disabled, true); } finally { f.restore(); }
});
test('partial-write warning reports completed writes without implying untouched files', async () => {
  const f=await fixture();try{f.controller.result={cancelled:false,changedCount:0,unchangedCount:0,failureCount:1,backupCount:1,status:f.snapshot,warning:'Puede haber una escritura parcial. Conserva las copias.'};f.render();assert.match(f.get('result').textContent,/0 escrituras completadas/);assert.match(f.get('result-warning').textContent,/escritura parcial/);}finally{f.restore();}
});
