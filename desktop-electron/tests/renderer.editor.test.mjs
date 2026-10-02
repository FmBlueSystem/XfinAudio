import assert from 'node:assert/strict';
import test from 'node:test';
import { SavedPlaylistEditor } from '../.out/renderer/editor.js';
const track = (id, patch = {}) => ({ id, title: id, artist: 'Artista', bpm: 120, key: '8A', energy: 5, duration: 60, missing: false, ...patch });
const snapshot = (patch = {}) => ({ editId: 'session-1', id: '1', name: 'Mi sesión', revision: 'r1', tracks: [track('a'), track('b', { missing: true }), track('a')], missingTrackCount: 1, ...patch });
const proposal = (tracks) => ({ editId: 'session-1', previewId: 'proposal-1', revision: 'r1', tracks, assessment: { description: 'Propuesta real del motor', readiness: 'needs_review', qualityScore: 0.75, warnings: ['Aviso real'] } });
function fixture(overrides = {}) {
  const calls = []; const dirtiness = []; let busy = false; let revision = 0; let routes = 0;
  const api = {
    openPlaylistEditor: async (input) => { calls.push(['open', input]); return snapshot({ id: input.playlistId }); },
    savePlaylistEdit: async (input) => { calls.push(['save', input]); return snapshot({ editId: 'session-2', revision: 'r2', name: input.name, tracks: input.trackIds.map((id) => track(id)) }); },
    discardPlaylistEdit: async (input) => { calls.push(['discard', input]); return snapshot({ editId: 'session-3' }); },
    previewPlaylistEdit: async (input) => { calls.push(['preview', input]); return proposal([track('b', { missing: true }), track('a')]); },
    ...overrides,
  };
  const host = {
    canAct: () => !busy, changed: () => {}, dirtyChanged: (dirty) => dirtiness.push(dirty), navigate: () => { routes++; },
    perform: async (_label, task, apply, failure) => {
      if (busy) return; busy = true; const started = revision;
      try { const result = await task(); apply(result, started === revision); } catch (error) { failure(error); } finally { busy = false; }
    },
  };
  const editor = new SavedPlaylistEditor(api, host);
  return { editor, calls, dirtiness, routes: () => routes, leave: () => { revision++; editor.invalidatePreview(); }, unlock: () => { busy = false; } };
}
test('editor retains duplicate occurrences and missing files while moving/removing by index', async () => {
  const f = fixture(); await f.editor.open('1'); assert.equal(f.editor.dirty, false);
  f.editor.move(2, -1); assert.deepEqual(f.editor.draft.tracks.map((track) => track.id), ['a', 'a', 'b']); assert.equal(f.editor.draft.tracks[2].missing, true);
  f.editor.remove(0); assert.deepEqual(f.editor.draft.tracks.map((track) => track.id), ['a', 'b']); assert.equal(f.editor.dirty, true); assert.equal(f.dirtiness.at(-1), true);
  f.editor.move(-1, 1); f.editor.move(1, 1); f.editor.remove(99); assert.deepEqual(f.editor.draft.tracks.map((track) => track.id), ['a', 'b']);
});
test('dirty draft survives navigation and same-set reopening without a second backend open', async () => {
  const f = fixture(); await f.editor.open('1'); f.editor.rename('Borrador sin guardar'); f.editor.remove(1); f.leave(); await f.editor.open('1');
  assert.equal(f.editor.draft.name, 'Borrador sin guardar'); assert.equal(f.editor.draft.tracks.length, 2); assert.equal(f.calls.filter(([method]) => method === 'open').length, 1); assert.equal(f.editor.dirty, true); assert.equal(f.routes(), 2);
});
test('opening another set requires explicit discard and can be cancelled without writes', async () => {
  const f = fixture(); await f.editor.open('1'); f.editor.rename('Borrador'); await f.editor.open('2');
  assert.equal(f.editor.pendingPlaylistId, '2'); assert.equal(f.editor.draft.id, '1'); assert.equal(f.calls.length, 1);
  f.editor.cancelSwitch(); assert.equal(f.editor.pendingPlaylistId, null); assert.equal(f.editor.dirty, true);
  await f.editor.open('2'); await f.editor.confirmSwitch(); assert.deepEqual(f.calls.map(([method]) => method), ['open', 'discard', 'open']); assert.equal(f.editor.draft.id, '2'); assert.equal(f.editor.dirty, false);
});
test('explicit save persists draft name and ordered IDs including legitimate duplicates', async () => {
  const f = fixture(); await f.editor.open('1'); f.editor.rename('  Nuevo nombre  '); f.editor.move(1, -1); assert.equal(f.calls.length, 1); await f.editor.save();
  assert.deepEqual(f.calls[1], ['save', { editId: 'session-1', name: 'Nuevo nombre', trackIds: ['b', 'a', 'a'] }]); assert.equal(f.editor.draft.editId, 'session-2'); assert.equal(f.editor.dirty, false); assert.equal(f.dirtiness.at(-1), false); await f.editor.save(); assert.equal(f.calls.length, 2);
});
test('save failure and revision conflict preserve the dirty draft and show a safe conflict', async () => {
  const f = fixture({ savePlaylistEdit: async () => { const error = new Error('stale_edit'); error.code = 'stale_edit'; throw error; } });
  await f.editor.open('1'); f.editor.remove(1); await f.editor.save(); assert.equal(f.editor.draft.editId, 'session-1'); assert.deepEqual(f.editor.draft.tracks.map((track) => track.id), ['a', 'a']); assert.equal(f.editor.dirty, true); assert.match(f.editor.error, /cambi[oó]|conflicto/i); assert.equal(f.dirtiness.at(-1), true);
});
test('explicit discard reloads saved snapshot and failed discard does not erase edits', async () => {
  let fail = true; const f = fixture({ discardPlaylistEdit: async () => { if (fail) throw new Error('Sin conexión'); return snapshot({ editId: 'session-new' }); } });
  await f.editor.open('1'); f.editor.remove(0); await f.editor.discard(); assert.equal(f.editor.dirty, true); assert.equal(f.editor.draft.tracks.length, 2);
  fail = false; await f.editor.discard(); assert.equal(f.editor.dirty, false); assert.equal(f.editor.draft.tracks.length, 3); assert.equal(f.editor.draft.editId, 'session-new');
});
test('offline proposal is read-only until Apply; Apply modifies draft but never saves', async () => {
  const f = fixture(); await f.editor.open('1'); f.editor.setRequest('acorta a 10 temas'); await f.editor.requestPreview(); assert.equal(f.editor.dirty, false); assert.equal(f.editor.draft.tracks.length, 3); assert.equal(f.editor.preview.assessment.description, 'Propuesta real del motor');
  assert.deepEqual(f.calls[1], ['preview', { editId: 'session-1', trackIds: ['a', 'b', 'a'], request: 'acorta a 10 temas' }]); f.editor.applyPreview(); assert.equal(f.editor.dirty, true); assert.deepEqual(f.editor.draft.tracks.map((track) => track.id), ['b', 'a']); assert.equal(f.editor.preview, null); assert.equal(f.calls.length, 2); await f.editor.save(); assert.equal(f.calls.at(-1)[0], 'save');
});
test('manual edits, request changes and navigation invalidate existing previews', async () => {
  const f = fixture(); await f.editor.open('1'); f.editor.setRequest('sube la energía'); await f.editor.requestPreview(); f.editor.move(0, 1); assert.equal(f.editor.preview, null);
  await f.editor.requestPreview(); f.editor.setRequest('acorta a 10 temas'); assert.equal(f.editor.preview, null); await f.editor.requestPreview(); f.leave(); assert.equal(f.editor.preview, null); f.editor.applyPreview(); assert.deepEqual(f.editor.draft.tracks.map((track) => track.id), ['b', 'a', 'a']);
});
test('late previews after navigation or manual context change never become applicable', async () => {
  for (const change of [(f) => f.leave(), (f) => { f.unlock(); f.editor.remove(1); }]) {
    let resolve; const f = fixture({ previewPlaylistEdit: () => new Promise((done) => { resolve = done; }) }); await f.editor.open('1'); f.editor.setRequest('sube la energía'); const pending = f.editor.requestPreview(); change(f); resolve(proposal([track('a')])); await pending; assert.equal(f.editor.preview, null); f.editor.applyPreview(); assert.ok(f.editor.draft.tracks.length >= 2);
  }
});
test('busy operations block repeated saves and stale opening never navigates', async () => {
  let resolve; const f = fixture({ openPlaylistEditor: () => new Promise((done) => { resolve = done; }) }); const pending = f.editor.open('1'); await f.editor.open('2'); f.leave(); resolve(snapshot()); await pending; assert.equal(f.routes(), 0); assert.equal(f.editor.draft, null);
  let finish; const g = fixture({ savePlaylistEdit: () => new Promise((done) => { finish = done; }) }); await g.editor.open('1'); g.editor.remove(0); const saving = g.editor.save(); await g.editor.save(); g.editor.rename('Late'); assert.equal(g.editor.draft.name, 'Mi sesión'); finish(snapshot({ editId: 'session-saved' })); await saving; assert.equal(g.editor.dirty, false);
});
test('invalid names cannot save but explicitly empty manual drafts can', async () => {
  const f = fixture(); await f.editor.open('1'); f.editor.rename('  '); await f.editor.save(); assert.equal(f.calls.length, 1); f.editor.rename('x'.repeat(201)); await f.editor.save(); assert.equal(f.calls.length, 1); f.editor.rename('Nuevo'); while (f.editor.draft.tracks.length) f.editor.remove(0); await f.editor.save(); assert.equal(f.calls.length, 2); assert.deepEqual(f.calls.at(-1)[1].trackIds, []);
});

test('serialized stale_edit discard failure explicitly reloads current set without losing draft early', async () => {
  let reload; const f = fixture({ discardPlaylistEdit: async () => { throw new Error('[stale_edit] Open saved playlist again'); }, openPlaylistEditor: async ({ playlistId }) => { if (reload) return snapshot({ id: playlistId, editId: 'fresh-after-scan', name: 'Guardada actual' }); return snapshot(); } });
  await f.editor.open('1'); f.editor.rename('Borrador'); reload = true; await f.editor.discard(); assert.equal(f.editor.draft.editId, 'fresh-after-scan'); assert.equal(f.editor.draft.name, 'Guardada actual'); assert.equal(f.editor.dirty, false);
});

test('context reset invalidates preview even when defensive dirty-draft preservation applies', async () => {
  const f = fixture(); await f.editor.open('1'); f.editor.rename('Borrador'); f.editor.setRequest('sube la energía'); await f.editor.requestPreview(); assert.ok(f.editor.preview);
  f.editor.resetAfterScan(); assert.equal(f.editor.preview, null); assert.equal(f.editor.draft.name, 'Borrador'); assert.equal(f.editor.dirty, true);
});

test('late opening of a different clean set never leaves the invalidated old session reusable', async () => {
  let finish; const f = fixture({ openPlaylistEditor: ({ playlistId }) => playlistId === '1' ? Promise.resolve(snapshot()) : new Promise((resolve) => { finish = resolve; }) });
  await f.editor.open('1'); const next = f.editor.open('2'); f.leave(); finish(snapshot({ id: '2', editId: 'edit-2' })); await next;
  assert.equal(f.editor.draft, null);
});

test('preview cannot send more than 500 source references', async () => {
  const f = fixture({ openPlaylistEditor: async () => snapshot({ tracks: Array.from({ length: 501 }, () => track('a')) }) });
  await f.editor.open('1'); f.editor.setRequest('acorta a 10 temas'); await f.editor.requestPreview(); assert.equal(f.calls.length, 0);
});

test('reopening a clean same-ID set refreshes externally changed name, order and edit token', async () => {
  let count = 0; const f = fixture({ openPlaylistEditor: async () => ++count === 1 ? snapshot() : snapshot({ name: 'Nombre actualizado', editId: 'external-refresh', revision: 'r2', tracks: [track('b'), track('a')] }) });
  await f.editor.open('1'); await f.editor.open('1'); assert.equal(count, 2); assert.equal(f.editor.draft.name, 'Nombre actualizado'); assert.equal(f.editor.draft.editId, 'external-refresh'); assert.deepEqual(f.editor.draft.tracks.map((track) => track.id), ['b', 'a']); assert.equal(f.editor.dirty, false);
});
