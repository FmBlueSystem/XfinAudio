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

// --- Improvement preview controller (bounded AI proposal) ---

const h64 = (seed) => String(seed).repeat(64).slice(0, 64);
const hexKey = (index) => index.toString(16).padStart(2, '0').repeat(32);
const publicTrack = (name, patch = {}) => ({ id: h64(name), title: `Título ${name}`, artist: 'Artista', bpm: 120, key: '8A', energy: 5, duration: 60, genre: 'Techno', audioFormat: 'flac', audioCodec: 'flac', bitrateKbps: 900, bitrateMode: 'VBR', status: 'ok', missingFields: [], missing: false, ...patch });
const trackById = (id) => publicTrack('seed', { id });
const improvementEditId = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const improvementSnapshot = (patch = {}) => ({ editId: improvementEditId, id: '1', name: 'Mi sesión', revision: 'r1', tracks: [publicTrack('a'), publicTrack('b'), publicTrack('c')], missingTrackCount: 0, ...patch });
const improvement = (patch = {}) => ({
  proposalId: 'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee', digest: 'f'.repeat(64), sourceRevision: 'r1',
  before: [publicTrack('a'), publicTrack('b'), publicTrack('c')], after: [publicTrack('c'), publicTrack('a'), publicTrack('d')],
  assessment: { description: 'Motor local', readiness: 'needs_review', qualityScore: 0.75, warnings: ['Aviso local'] },
  addedIds: [h64('d')], removedIds: [h64('b')], ...patch,
});
const afterIds = [h64('c'), h64('a'), h64('d')];
function improvementFixture(overrides = {}) {
  const calls = []; const dirtiness = []; let busy = false; let revision = 0; let routes = 0;
  const api = {
    openPlaylistEditor: async (input) => { calls.push(['open', input]); return improvementSnapshot({ id: input.playlistId }); },
    previewPlaylistEdit: async (input) => { calls.push(['preview', input]); return { editId: input.editId, previewId: 'legacy-1', revision: 'r1', tracks: [], assessment: { description: 'legacy', readiness: 'needs_review', qualityScore: 0.5, warnings: [] } }; },
    savePlaylistEdit: async (input) => { calls.push(['save', input]); return improvementSnapshot({ editId: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', revision: 'r2', name: input.name, tracks: input.trackIds.map(trackById) }); },
    savePlaylistImprovement: async (input) => { calls.push(['saveImprovement', input]); return improvementSnapshot({ editId: 'cccccccc-cccc-4ccc-8ccc-cccccccccccc', revision: 'r3', name: input.name, tracks: input.draftIds.map(trackById) }); },
    discardPlaylistEdit: async (input) => { calls.push(['discard', input]); return improvementSnapshot({ editId: 'dddddddd-dddd-4ddd-8ddd-dddddddddddd', revision: 'r4' }); },
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
  return { editor, calls, dirtiness, routes: () => routes, leave: () => { revision++; editor.invalidatePreview(); } };
}

test('improvement preview requires the exact before-order and current session revision', async () => {
  const f = improvementFixture(); await f.editor.open('1');
  assert.equal(f.editor.setImprovementPreview(improvement()), true);
  assert.deepEqual(f.editor.improvement.after.map((track) => track.id), afterIds);
  assert.equal(f.editor.improvement.proposalId, 'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee');
  f.editor.move(0, 1);
  assert.equal(f.editor.improvement, null);
  assert.equal(f.editor.setImprovementPreview(improvement()), false);
  assert.equal(f.editor.improvement, null);
  assert.equal(f.editor.improvementBound, false);
  const g = improvementFixture(); await g.editor.open('1');
  assert.equal(g.editor.setImprovementPreview(improvement({ sourceRevision: 'r9' })), false);
  assert.equal(g.editor.setImprovementPreview(improvement(), 'ffffffff-ffff-4fff-8fff-ffffffffffff'), false);
  assert.equal(g.editor.setImprovementPreview(improvement({ editId: 'ffffffff-ffff-4fff-8fff-ffffffffffff' })), false);
  assert.equal(g.editor.improvement, null);
});

test('improvement preview rejects malformed, oversized or unsafe payloads', async () => {
  const f = improvementFixture(); await f.editor.open('1');
  const rejected = [
    improvement({ proposalId: '../proposal' }),
    improvement({ digest: 'f'.repeat(63) }),
    improvement({ after: [publicTrack('a')] }),
    improvement({ after: Array.from({ length: 81 }, (_, index) => trackById(hexKey(index))) }),
    improvement({ after: [publicTrack('a'), publicTrack('a')] }),
    improvement({ after: [publicTrack('a', { id: 'short' })] }),
    improvement({ after: [publicTrack('a', { missing: 'no' })] }),
    improvement({ after: [publicTrack('a', { bpm: Number.POSITIVE_INFINITY })] }),
    improvement({ assessment: { description: 'x', readiness: 'unknown', qualityScore: 1, warnings: [] } }),
    improvement({ assessment: { description: 'x', readiness: 'ready', qualityScore: Number.NaN, warnings: [] } }),
    improvement({ assessment: { description: 'x', readiness: 'ready', qualityScore: 1, warnings: [1] } }),
    improvement({ assessment: null }),
    improvement({ before: [publicTrack('b'), publicTrack('a'), publicTrack('c')] }),
    null, [], 'improvement',
  ];
  for (const value of rejected) { assert.equal(f.editor.setImprovementPreview(value), false); assert.equal(f.editor.improvement, null); }
  const unsafe = { ...improvement({ after: [{ ...publicTrack('d'), path: '/etc/passwd', evil: true }, publicTrack('c'), publicTrack('a')], addedIds: ['/etc/passwd'], removedIds: ['nonsense'] }) };
  assert.equal(f.editor.setImprovementPreview(unsafe), true);
  assert.equal('path' in f.editor.improvement.after[0], false);
  assert.equal('evil' in f.editor.improvement.after[0], false);
  assert.deepEqual(f.editor.improvement.addedIds, [h64('d')]);
  assert.deepEqual(f.editor.improvement.removedIds, [h64('b')]);
});

test('improvement preview is read-only until an explicit apply', async () => {
  const f = improvementFixture(); await f.editor.open('1');
  f.editor.setImprovementPreview(improvement());
  assert.deepEqual(f.calls.map(([method]) => method), ['open']);
  assert.equal(f.editor.dirty, false);
  assert.deepEqual(f.editor.draft.tracks.map((track) => track.id), [h64('a'), h64('b'), h64('c')]);
  assert.equal(f.editor.improvementBound, false);
  await f.editor.save();
  assert.deepEqual(f.calls.map(([method]) => method), ['open']);
});

test('applying an improvement updates only the draft and binds the exact proposal for a dedicated save', async () => {
  const f = improvementFixture(); await f.editor.open('1');
  f.editor.setImprovementPreview(improvement());
  assert.equal(f.editor.applyImprovementPreview(), true);
  assert.deepEqual(f.editor.draft.tracks.map((track) => track.id), afterIds);
  assert.equal(f.editor.dirty, true);
  assert.equal(f.editor.improvementBound, true);
  assert.deepEqual(f.calls.map(([method]) => method), ['open']);
  await f.editor.save();
  assert.deepEqual(f.calls.at(-1), ['saveImprovement', { editId: improvementEditId, name: 'Mi sesión', proposalId: 'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee', digest: 'f'.repeat(64), draftIds: afterIds }]);
  assert.equal(f.calls.some(([method]) => method === 'save'), false);
  assert.equal(f.editor.improvementBound, false);
  assert.equal(f.editor.dirty, false);
});

test('manual edits after apply revoke the binding and restore the ordinary save', async () => {
  for (const change of [(editor) => editor.move(0, 1), (editor) => editor.remove(0), (editor) => editor.rename('Otro nombre'), (editor) => editor.setRequest('acorta')]) {
    const f = improvementFixture(); await f.editor.open('1'); f.editor.setImprovementPreview(improvement()); f.editor.applyImprovementPreview();
    assert.equal(f.editor.improvementBound, true);
    change(f.editor);
    assert.equal(f.editor.improvementBound, false);
    await f.editor.save();
    assert.equal(f.calls.filter(([method]) => method === 'save').length, 1);
    assert.equal(f.calls.some(([method]) => method === 'saveImprovement'), false);
    assert.deepEqual(f.calls.at(-1)[1], { editId: improvementEditId, name: f.editor.draft.name.trim(), trackIds: f.editor.draft.tracks.map((track) => track.id) });
  }
});

test('the ordinary save stays identical when no improvement is bound', async () => {
  const f = improvementFixture(); await f.editor.open('1'); f.editor.move(0, 1); await f.editor.save();
  assert.deepEqual(f.calls.at(-1), ['save', { editId: improvementEditId, name: 'Mi sesión', trackIds: [h64('b'), h64('a'), h64('c')] }]);
});

test('a blocked assessment is visible but can never be applied to the draft', async () => {
  const f = improvementFixture(); await f.editor.open('1');
  assert.equal(f.editor.setImprovementPreview(improvement({ assessment: { description: 'Bloqueado', readiness: 'blocked', qualityScore: 0, warnings: ['Metadatos incompletos'] } })), true);
  assert.ok(f.editor.improvement);
  assert.equal(f.editor.applyImprovementPreview(), false);
  assert.deepEqual(f.editor.draft.tracks.map((track) => track.id), [h64('a'), h64('b'), h64('c')]);
  assert.equal(f.editor.improvementBound, false);
});

test('a late improvement result never overwrites a newer draft', async () => {
  const f = improvementFixture(); await f.editor.open('1'); const late = improvement();
  f.editor.setImprovementPreview(late); f.editor.applyImprovementPreview(); f.editor.move(0, 1);
  assert.equal(f.editor.setImprovementPreview(late), false);
  assert.equal(f.editor.improvement, null);
  assert.equal(f.editor.applyImprovementPreview(), false);
  assert.deepEqual(f.editor.draft.tracks.map((track) => track.id), [h64('a'), h64('c'), h64('d')]);
  const g = improvementFixture(); await g.editor.open('1'); g.editor.setImprovementPreview(late); await g.editor.discard();
  assert.equal(g.editor.setImprovementPreview(late), false);
  assert.equal(g.editor.improvementBound, false);
});

test('opening, discarding or resetting the editor revokes the improvement binding', async () => {
  const f = improvementFixture(); await f.editor.open('1'); f.editor.setImprovementPreview(improvement()); f.editor.applyImprovementPreview(); await f.editor.discard();
  assert.equal(f.editor.improvementBound, false);
  const g = improvementFixture(); await g.editor.open('1'); g.editor.setImprovementPreview(improvement()); g.editor.applyImprovementPreview(); g.editor.resetAfterScan();
  assert.equal(g.editor.improvementBound, false);
  const h = improvementFixture(); await h.editor.open('1'); h.editor.setImprovementPreview(improvement()); h.editor.applyImprovementPreview(); await h.editor.open('2');
  assert.equal(h.editor.improvementBound, false);
});

test('a newer improvement preview replaces the previous one for the same draft', async () => {
  const f = improvementFixture(); await f.editor.open('1');
  f.editor.setImprovementPreview(improvement());
  const newer = improvement({ proposalId: '99999999-9999-4999-8999-999999999999', after: [publicTrack('b'), publicTrack('d'), publicTrack('a')] });
  assert.equal(f.editor.setImprovementPreview(newer), true);
  assert.equal(f.editor.improvement.proposalId, '99999999-9999-4999-8999-999999999999');
  assert.deepEqual(f.editor.draft.tracks.map((track) => track.id), [h64('a'), h64('b'), h64('c')]);
});

test('a rejected improvement payload never replaces a valid preview for the same draft', async () => {
  const f = improvementFixture(); await f.editor.open('1');
  assert.equal(f.editor.setImprovementPreview(improvement()), true);
  assert.equal(f.editor.setImprovementPreview(improvement({ proposalId: 'no', sourceRevision: 'r9' })), false);
  assert.equal(f.editor.improvement.proposalId, 'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee');
});

test('a failed improvement save keeps the bound draft and never falls back to the manual save', async () => {
  let attempts = 0;
  const f = improvementFixture({ savePlaylistImprovement: async () => { attempts++; const error = new Error('stale_edit'); error.code = 'stale_edit'; throw error; } });
  await f.editor.open('1'); f.editor.setImprovementPreview(improvement()); f.editor.applyImprovementPreview(); await f.editor.save();
  assert.equal(f.calls.filter(([method]) => method === 'save').length, 0);
  assert.equal(attempts, 1);
  assert.deepEqual(f.editor.draft.tracks.map((track) => track.id), afterIds);
  assert.equal(f.editor.improvementBound, true);
  assert.match(f.editor.error, /cambi[oó]|conflicto/i);
});
