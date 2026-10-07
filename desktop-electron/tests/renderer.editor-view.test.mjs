import assert from 'node:assert/strict';
import test from 'node:test';
import { createEditorView } from '../.out/renderer/editor-view.js';
class Element extends EventTarget {
  constructor(tag = 'div') { super(); this.tagName = tag; }
  children = []; attrs = {}; dataset = {}; textContent = ''; value = ''; disabled = false; hidden = false;
  setAttribute(key, value) { this.attrs[key] = String(value); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  focus() { this.focused = true; }
  set innerHTML(_) { throw new Error('No unsafe HTML'); }
}
const all = (root) => [root, ...root.children.flatMap(all)];
const text = (root) => [root.textContent, ...root.children.map(text)].join(' ');
const click = (node) => { assert.ok(node); if (!node.disabled) node.dispatchEvent(new Event('click')); };
function fixture(hostPatch = {}) {
  const before = globalThis.document; globalThis.document = { createElement: (tag) => new Element(tag) };
  const calls = []; const tracks = [{ id: 'a', title: '<img src=x onerror=alert(1)>', artist: 'Artista', missing: false, bpm: 120, key: '8A', energy: 5, duration: 60 }, { id: 'b', title: 'Ausente', artist: 'Artista', missing: true, bpm: null, key: null, energy: null, duration: null }];
  const editor = { draft: { id: '1', name: 'Prueba', tracks }, dirty: true, canSave: true, error: '', preview: null, improvement: null, improvementBound: false, pendingPlaylistId: null, request: '',
    move: (...args) => calls.push(['move', ...args]), remove: (...args) => calls.push(['remove', ...args]), rename: (...args) => calls.push(['rename', ...args]), save: async () => calls.push(['save']), discard: async () => calls.push(['discard']), requestPreview: async () => calls.push(['preview']), applyPreview: () => calls.push(['apply']), applyImprovementPreview: () => calls.push(['applyImprovement']), setRequest: (...args) => calls.push(['request', ...args]), confirmSwitch: async () => calls.push(['confirm']), cancelSwitch: () => calls.push(['cancel']), };
  let busy = false; const root = new Element(); const render = createEditorView(root, editor, { canAct: () => !busy, play: (track) => calls.push(['play', track.id]), improvement: () => ({ available: true, hint: '' }), openImprovement: () => calls.push(['improve']), improvementApplied: () => {}, ...hostPatch }); render();
  return { root, editor, render, calls, nodes: () => all(root), get: (id) => all(root).find((node) => node.id === `editor-${id}`), busy: () => { busy = true; render(); }, restore: () => { globalThis.document = before; } };
}
test('accessible Spanish editor keeps missing rows visible and metadata is text only', () => {
  const f = fixture(); try {
    assert.match(text(f.root), /Cambios sin guardar/); assert.match(text(f.root), /Archivo no disponible/); assert.match(text(f.root), /<img src=x/);
    assert.ok(!f.nodes().some((node) => ['script', 'img'].includes(node.tagName)));
    for (const id of ['name', 'request']) assert.ok(f.nodes().some((node) => node.tagName === 'label' && node.attrs.for === `editor-${id}`));
    assert.ok(f.nodes().filter((node) => node.tagName === 'th').every((node) => node.scope === 'col'));
    assert.equal(f.get('dirty').attrs['aria-live'], 'polite');
    const rows = f.nodes().filter((node) => node.dataset.editorIndex !== undefined); assert.equal(rows.length, 2);
    assert.equal(all(rows[0]).find((node) => node.attrs['aria-label']?.startsWith('Subir')).disabled, true);
    assert.equal(all(rows[1]).find((node) => node.attrs['aria-label']?.startsWith('Bajar')).disabled, true);
    assert.equal(all(rows[1]).find((node) => node.attrs['aria-label']?.startsWith('Escuchar')).disabled, true);
  } finally { f.restore(); }
});
test('row controls use occurrence indexes and Save/Discard remain explicit separate actions', () => {
  const f = fixture(); try {
    click(f.nodes().find((node) => node.attrs['aria-label']?.startsWith('Bajar 1'))); click(f.nodes().find((node) => node.attrs['aria-label']?.startsWith('Quitar 2'))); click(f.get('save')); click(f.get('discard'));
    assert.deepEqual(f.calls, [['move', 0, 1], ['remove', 1], ['save'], ['discard']]);
    f.busy(); assert.equal(f.get('save').disabled, true); assert.equal(f.get('discard').disabled, true); assert.equal(f.get('name').disabled, true); assert.equal(f.get('request').disabled, true);
  } finally { f.restore(); }
});
test('preview presents actual assessment and proposal order and Apply is separately gated', () => {
  const f = fixture(); try {
    f.editor.preview = { tracks: [...f.editor.draft.tracks].reverse(), assessment: { description: 'Evaluación original', readiness: 'needs_review', qualityScore: 0.42, warnings: ['Aviso del motor'] } }; f.render();
    for (const expected of ['Evaluación original', 'Aviso del motor', '0,42', 'Propuesta sin aplicar', 'Aplicar al borrador']) assert.ok(text(f.root).includes(expected), expected);
    assert.deepEqual(f.get('proposal-tracks').children.map((node) => node.textContent), ['1. Ausente · Artista · Archivo no disponible', '2. <img src=x onerror=alert(1)> · Artista']);
    click(f.get('apply')); assert.deepEqual(f.calls, [['apply']]); f.editor.preview.assessment.readiness = 'blocked'; f.render(); assert.equal(f.get('apply').disabled, true);
  } finally { f.restore(); }
});
test('discard-or-cancel prompt is explicit, keyboard reachable, and conflict does not clear draft', () => {
  const f = fixture(); try {
    f.editor.pendingPlaylistId = '2'; f.editor.error = 'La playlist cambió'; f.render(); assert.equal(f.get('switch').hidden, false); assert.equal(f.get('error').attrs.role, 'alert'); assert.match(text(f.root), /La playlist cambió/);
    click(f.get('switch-cancel')); click(f.get('switch-discard')); assert.deepEqual(f.calls, [['cancel'], ['confirm']]); assert.equal(f.editor.draft.tracks.length, 2);
  } finally { f.restore(); }
});

test('editor keeps its contextual return route and bounded standalone page', async () => {
  const { readFile } = await import('node:fs/promises'); const html = await readFile(new URL('../renderer/index.html', import.meta.url), 'utf8');
  assert.match(html, /id="tool-back"[^>]+type="button"/); assert.match(html, /data-route="playlists"/); assert.match(html, /id="page-editor"[^>]+aria-labelledby="editor-heading"/); assert.match(html, /id="editor-container"/);
});

test('moving a row restores a keyboard action on that row after the table is rebuilt', () => {
  const f = fixture(); try {
    f.editor.move = (index, direction) => { const tracks = [...f.editor.draft.tracks]; const next = index + direction; [tracks[index], tracks[next]] = [tracks[next], tracks[index]]; f.editor.draft = { ...f.editor.draft, tracks }; f.render(); };
    click(f.nodes().find((node) => node.attrs['aria-label']?.startsWith('Bajar 1')));
    const moved = f.nodes().find((node) => node.attrs['aria-label']?.startsWith('Subir 2')); assert.equal(moved.focused, true);
  } finally { f.restore(); }
});

test('the summary improvement CTA is explicit-only and states an actionable reason when unavailable', () => {
  const f = fixture(); try {
    const cta = f.get('improve'); assert.equal(cta.textContent, 'Mejorar con IA…'); assert.equal(cta.disabled, false);
    click(cta); assert.deepEqual(f.calls, [['improve']]);
  } finally { f.restore(); }
  const g = fixture({ improvement: () => ({ available: false, hint: 'La mejora con IA necesita entre 2 y 80 pistas en el borrador.' }) }); try {
    assert.equal(g.get('improve').disabled, true);
    assert.match(g.get('improve-hint').textContent, /2 y 80/);
    click(g.get('improve')); assert.equal(g.calls.some(([kind]) => kind === 'improve'), false);
  } finally { g.restore(); }
});

test('a read-only improvement preview renders numbered before/after rows, counts and assessment and mutates only on click', () => {
  const f = fixture(); try {
    f.editor.improvement = { before: f.editor.draft.tracks, after: [...f.editor.draft.tracks].reverse(), addedIds: ['x'.repeat(64)], removedIds: ['y'.repeat(64)], assessment: { description: 'Orden con mejor flujo', readiness: 'needs_review', qualityScore: 0.71, warnings: ['Transición justa'] } };
    f.render();
    assert.match(text(f.root), /antes/i); assert.match(text(f.root), /después/i);
    assert.deepEqual(f.get('improvement-before').children.map((node) => node.textContent), ['1. <img src=x onerror=alert(1)> · Artista', '2. Ausente · Artista · Archivo no disponible']);
    assert.deepEqual(f.get('improvement-after').children.map((node) => node.textContent), ['1. Ausente · Artista · Archivo no disponible · #2 → #1', '2. <img src=x onerror=alert(1)> · Artista · #1 → #2']);
    assert.equal(f.get('improvement-counts').textContent, '1 pista añadida · 1 pista quitada · 2 movidas');
    for (const expected of ['Orden con mejor flujo', 'Transición justa', '0,71', 'Aplicar mejora al borrador']) assert.ok(text(f.root).includes(expected), expected);
    assert.deepEqual(f.calls, []);
    click(f.get('improvement-apply')); assert.deepEqual(f.calls, [['applyImprovement']]);
    assert.ok(!f.nodes().some((node) => ['img', 'script'].includes(node.tagName)));
  } finally { f.restore(); }
});

test('the improvement diff marks only real moves inline and omits the moved clause when nothing moved', () => {
  const f = fixture(); try {
    const track = (id) => ({ id, title: id.toUpperCase(), artist: 'DJ', missing: false, bpm: null, key: null, energy: null, duration: null });
    const before = [track('a'), track('b'), track('c')]; const added = track('d');
    const assessment = { description: 'Motor local', readiness: 'ready', qualityScore: 1, warnings: [] };
    f.editor.improvement = { before, after: [before[0], before[2], before[1]], addedIds: [], removedIds: [], assessment };
    f.render();
    assert.deepEqual(f.get('improvement-after').children.map((node) => node.textContent), ['1. A · DJ', '2. C · DJ · #3 → #2', '3. B · DJ · #2 → #3']);
    assert.equal(f.get('improvement-before').children.map((node) => node.textContent).some((line) => line.includes('→')), false);
    assert.equal(f.get('improvement-counts').textContent, '0 pistas añadidas · 0 pistas quitadas · 2 movidas');
    f.editor.improvement = { before, after: [...before], addedIds: [], removedIds: [], assessment };
    f.render();
    assert.deepEqual(f.get('improvement-after').children.map((node) => node.textContent), ['1. A · DJ', '2. B · DJ', '3. C · DJ']);
    assert.equal(f.get('improvement-counts').textContent, '0 pistas añadidas · 0 pistas quitadas');
    f.editor.improvement = { before, after: [...before, added], addedIds: [added.id], removedIds: [], assessment };
    f.render();
    assert.deepEqual(f.get('improvement-after').children.map((node) => node.textContent), ['1. A · DJ', '2. B · DJ', '3. C · DJ', '4. D · DJ']);
    assert.equal(f.get('improvement-counts').textContent, '1 pista añadida · 0 pistas quitadas');
  } finally { f.restore(); }
});

test('the improvement apply button reports a successful transition and stays silent when the apply is refused', () => {
  const applied = []; const f = fixture({ improvementApplied: () => applied.push('applied') }); try {
    f.editor.improvement = { before: f.editor.draft.tracks, after: [...f.editor.draft.tracks].reverse(), addedIds: [], removedIds: [], assessment: { description: 'Motor local', readiness: 'ready', qualityScore: 1, warnings: [] } };
    f.render();
    assert.equal(f.get('improvement-apply').disabled, false);
    f.editor.applyImprovementPreview = () => { f.calls.push(['applyImprovement']); return true; };
    click(f.get('improvement-apply'));
    assert.deepEqual(applied, ['applied']);
    f.editor.applyImprovementPreview = () => { f.calls.push(['applyImprovement']); return false; };
    click(f.get('improvement-apply'));
    assert.deepEqual(applied, ['applied']);
    assert.deepEqual(f.calls, [['applyImprovement'], ['applyImprovement']]);
  } finally { f.restore(); }
});

test('a blocked improvement states the block and disables apply while the bound save label stays honest', () => {
  const f = fixture(); try {
    assert.equal(f.get('save').textContent, 'Guardar cambios');
    f.editor.improvement = { before: f.editor.draft.tracks, after: f.editor.draft.tracks, addedIds: [], removedIds: [], assessment: { description: 'Bloqueada', readiness: 'blocked', qualityScore: 0, warnings: ['Metadatos incompletos'] } };
    f.editor.improvementBound = true; f.render();
    assert.equal(f.get('improvement-apply').disabled, true);
    assert.equal(f.get('improvement-blocked').hidden, false);
    assert.match(f.get('improvement-blocked').textContent, /bloqueada/i);
    assert.equal(f.get('save').textContent, 'Guardar mejora');
    f.editor.improvementBound = false; f.render(); assert.equal(f.get('save').textContent, 'Guardar cambios');
  } finally { f.restore(); }
});

test('the legacy local proposal stays reachable beside the improvement surface', () => {
  const f = fixture(); try {
    f.editor.preview = { tracks: [...f.editor.draft.tracks].reverse(), assessment: { description: 'Evaluación local', readiness: 'ready', qualityScore: 1, warnings: [] } };
    f.editor.improvement = { before: f.editor.draft.tracks, after: [...f.editor.draft.tracks].reverse(), addedIds: [], removedIds: [], assessment: { description: 'Motor local', readiness: 'needs_review', qualityScore: 0.8, warnings: [] } };
    f.render();
    click(f.get('apply')); click(f.get('improvement-apply'));
    assert.deepEqual(f.calls, [['apply'], ['applyImprovement']]);
  } finally { f.restore(); }
});
