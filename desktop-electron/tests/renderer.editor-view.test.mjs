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
function fixture() {
  const before = globalThis.document; globalThis.document = { createElement: (tag) => new Element(tag) };
  const calls = []; const tracks = [{ id: 'a', title: '<img src=x onerror=alert(1)>', artist: 'Artista', missing: false, bpm: 120, key: '8A', energy: 5, duration: 60 }, { id: 'b', title: 'Ausente', artist: 'Artista', missing: true, bpm: null, key: null, energy: null, duration: null }];
  const editor = { draft: { id: '1', name: 'Prueba', tracks }, dirty: true, canSave: true, error: '', preview: null, pendingPlaylistId: null, request: '',
    move: (...args) => calls.push(['move', ...args]), remove: (...args) => calls.push(['remove', ...args]), rename: (...args) => calls.push(['rename', ...args]), save: async () => calls.push(['save']), discard: async () => calls.push(['discard']), requestPreview: async () => calls.push(['preview']), applyPreview: () => calls.push(['apply']), setRequest: (...args) => calls.push(['request', ...args]), confirmSwitch: async () => calls.push(['confirm']), cancelSwitch: () => calls.push(['cancel']), };
  let busy = false; const root = new Element(); const render = createEditorView(root, editor, { canAct: () => !busy, play: (track) => calls.push(['play', track.id]) }); render();
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
