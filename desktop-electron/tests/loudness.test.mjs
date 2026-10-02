import assert from 'node:assert/strict';
import test from 'node:test';
import { LoudnessController } from '../.out/renderer/loudness.js';
const id = (n) => n.toString(16).padStart(64, '0');
const track = (n) => ({ id: id(n), title: `Pista ${n}`, artist: 'DJ', bpm: null, key: null, energy: null, duration: 120 });
const entry = (n) => ({ track: track(n), state: 'unmeasured', complete: false, lufs: null, lra: null, truePeak: null });
const snapshot = (patch = {}, count = 3) => ({ revision: 'a'.repeat(64), enabled: true, targetLufs: -10, toleranceLu: 2, available: true, reason: 'ready', totalTracks: count, tracks: Array.from({ length: count }, (_, n) => entry(n + 1)), ...patch });
const preview = (tracks = [track(1)], force = false) => ({ previewId: '12345678-1234-4123-8123-123456789012', trackCount: tracks.length, backupBytes: 100, force, tracks, replaceComments: true });
const result = (patch = {}) => ({ cancelled: false, changedCount: 1, unchangedCount: 0, failureCount: 0, backupCount: 1, status: snapshot(), ...patch });
function fixture(overrides = {}, count = 3) {
  const calls = []; const applied = []; const dirty = []; let busy = false; let online = true; let route = 0;
  const api = { getLoudnessStatus: async () => { calls.push(['get']); return snapshot({}, count); }, saveLoudnessSettings: async (input) => { calls.push(['save', input]); return snapshot({ ...input, revision: 'b'.repeat(64) }, count); }, previewLoudness: async (input) => { calls.push(['preview', input]); return preview(input.trackIds.map((value) => track(parseInt(value, 16))), input.force); }, runLoudness: async (input) => { calls.push(['run', input]); return result(); }, ...overrides };
  const controller = new LoudnessController(api, { canAct: () => online && !busy, changed: () => {}, dirtyChanged: (value) => dirty.push(value), applied: (value, reason) => applied.push([value, reason]), perform: async (_label, task, apply, failure) => { if (busy) return; busy = true; const start = route; try { apply(await task(), start === route); } catch (error) { failure(error); } finally { busy = false; } } });
  return { controller, calls, applied, dirty, leave: () => { route++; }, disconnect: () => { online = false; controller.invalidateContext(); } };
}
test('loads real status, keeps edits local and preserves dirty draft until explicit discard', async () => {
  const f = fixture(); await f.controller.load(); assert.equal(f.controller.snapshot.totalTracks, 3); assert.equal(f.applied[0][1], 'load'); f.controller.setTarget(-14); f.controller.setTolerance(3); f.controller.setEnabled(false); f.leave(); await f.controller.load(); assert.equal(f.calls.length, 1); assert.equal(f.controller.dirty, true); assert.match(f.controller.error, /descarta/i); f.controller.discard(); assert.equal(f.controller.snapshot.targetLufs, -10); assert.equal(f.controller.dirty, false); assert.equal(f.applied.length, 1);
});
test('settings use original finite bounds and booleans, send only settings and revision', async () => {
  const f = fixture(); await f.controller.load(); for (const v of [NaN, Infinity, -31, 1, '-10', null]) f.controller.setTarget(v); for (const v of [NaN, Infinity, -1, 11, '2', null]) f.controller.setTolerance(v); for (const v of [1, 'true', null]) f.controller.setEnabled(v); assert.equal(f.controller.dirty, false); f.controller.setTarget(-30); f.controller.setTolerance(10); f.controller.setEnabled(false); await f.controller.save(); assert.deepEqual(f.calls.at(-1), ['save', { revision: 'a'.repeat(64), enabled: false, targetLufs: -30, toleranceLu: 10 }]); assert.equal(f.controller.dirty, false); assert.equal(f.applied.at(-1)[1], 'save');
});
test('stale_revision keeps draft and safe error, requires discard then refresh', async () => {
  const f = fixture({ saveLoudnessSettings: async () => { throw new Error('[stale_revision] /Users/private/settings'); } }); await f.controller.load(); f.controller.setTarget(-12); await f.controller.save(); assert.equal(f.controller.snapshot.targetLufs, -12); assert.equal(f.controller.canSave, false); assert.equal(f.controller.dirty, true); assert.match(f.controller.error, /descarta.*actualiza/i); assert.doesNotMatch(f.controller.error, /Users|stale_revision/); f.controller.discard(); await f.controller.load(); f.controller.setTarget(-11); assert.equal(f.controller.canSave, true);
});
test('known unique opaque selection is explicit, capped without truncating, and page selection keeps every intended ID', async () => {
  const f = fixture({}, 501); await f.controller.load(); f.controller.setSelection([id(1)]); f.controller.selectAll(); assert.deepEqual(f.controller.selectedIds, [id(1)]); assert.match(f.controller.error, /500/); f.controller.setSelection([id(1), id(1)]); assert.deepEqual(f.controller.selectedIds, [id(1)]); f.controller.setSelection(['/tmp/music.mp3']); assert.deepEqual(f.controller.selectedIds, [id(1)]); f.controller.clearSelection(); f.controller.selectPage(); assert.equal(f.controller.selectedIds.length, 100); f.controller.setPage(4); assert.equal(f.controller.visibleTracks.length, 100); f.controller.selectPage(); assert.equal(f.controller.selectedIds.length, 200); f.controller.setPage(5); assert.equal(f.controller.visibleTracks.length, 1); assert.equal(f.controller.pageCount, 6);
});
test('read-only preview binds exact IDs and settings/selection changes invalidate it', async () => {
  const f = fixture(); await f.controller.load(); f.controller.setSelection([id(1), id(3)]); await f.controller.requestPreview(); assert.deepEqual(f.calls.at(-1), ['preview', { trackIds: [id(1), id(3)], force: false }]); assert.equal(f.controller.canRun, true); assert.ok(!f.calls.some(([kind]) => kind === 'run')); f.controller.toggleTrack(id(2), true); assert.equal(f.controller.preview, null); await f.controller.requestPreview(); f.controller.setTarget(-11); assert.equal(f.controller.preview, null); assert.equal(f.controller.canPreview, false);
});
test('force reanalysis first requests one-track preview, never starts a write', async () => {
  const f = fixture(); await f.controller.load(); f.controller.setSelection([id(1), id(2)]); await f.controller.requestPreview(true); assert.equal(f.calls.length, 1); await f.controller.reanalyze(id(2)); assert.deepEqual(f.calls.at(-1), ['preview', { trackIds: [id(2)], force: true }]); assert.equal(f.controller.preview.force, true); assert.equal(f.controller.result, null);
});
test('explicit run sends only preview ID, blocks duplicates and retains truthful cancelled partial counts after navigation', async () => {
  let finish; let runs = 0; const f = fixture({ runLoudness: (input) => { runs++; assert.deepEqual(input, { previewId: preview().previewId }); return new Promise((resolve) => { finish = resolve; }); } }); await f.controller.load(); f.controller.setSelection([id(1)]); await f.controller.requestPreview(); const pending = f.controller.run(); await f.controller.run(); f.controller.setTarget(-15); f.leave(); finish(result({ cancelled: true })); await pending; assert.equal(runs, 1); assert.equal(f.controller.result.cancelled, true); assert.equal(f.controller.result.changedCount, 1); assert.equal(f.controller.snapshot.targetLufs, -10); assert.equal(f.controller.preview, null); assert.equal(f.applied.at(-1)[1], 'run');
});
test('library context invalidation clears selection and rejects late preview without reviving old status', async () => {
  let finish; const f = fixture({ previewLoudness: () => new Promise((resolve) => { finish = resolve; }) }); await f.controller.load(); f.controller.setSelection([id(1)]); const pending = f.controller.requestPreview(); f.controller.invalidateContext(); finish(preview()); await pending; assert.equal(f.controller.preview, null); assert.deepEqual(f.controller.selectedIds, []); assert.equal(f.controller.statusFresh, false); assert.equal(f.controller.canPreview, false);
});
test('context invalidation rejects late load/save status but preserves save draft', async () => {
  let finish; const f = fixture({ saveLoudnessSettings: () => new Promise((resolve) => { finish = resolve; }) }); await f.controller.load(); f.controller.setTarget(-12); const pending = f.controller.save(); f.controller.invalidateContext(); finish(snapshot({ targetLufs: -12, revision: 'b'.repeat(64) })); await pending; assert.equal(f.controller.snapshot.revision, 'a'.repeat(64)); assert.equal(f.controller.dirty, true); assert.equal(f.controller.statusFresh, false); assert.equal(f.applied.length, 1);
});
test('completed writes keep receipt counts if context changes but cannot revive old library data', async () => {
  let finish; const f = fixture({ runLoudness: () => new Promise((resolve) => { finish = resolve; }) }); await f.controller.load(); f.controller.setSelection([id(1)]); await f.controller.requestPreview(); const pending = f.controller.run(); f.controller.invalidateContext(); finish(result()); await pending; assert.equal(f.controller.result.backupCount, 1); assert.equal(f.controller.statusFresh, false); assert.deepEqual(f.controller.selectedIds, []); assert.equal(f.applied.length, 1);
});
test('disabled or missing engine never permits preview and disconnected controls preserve draft', async () => {
  for (const patch of [{ enabled: false }, { available: false, reason: 'missing_engine' }]) { const f = fixture({ getLoudnessStatus: async () => snapshot(patch) }); await f.controller.load(); f.controller.setSelection([id(1)]); await f.controller.requestPreview(); assert.equal(f.controller.canPreview, false); assert.equal(f.controller.preview, null); }
  const f = fixture(); await f.controller.load(); f.controller.setTarget(-11); f.disconnect(); f.controller.discard(); f.controller.setEnabled(false); await f.controller.save(); await f.controller.load(); assert.equal(f.controller.dirty, true); assert.equal(f.controller.snapshot.enabled, true); assert.equal(f.calls.length, 1);
});
test('malformed snapshots, mismatched previews and backend errors fail closed without raw paths', async () => {
  for (const patch of [{ revision: 'bad' }, { targetLufs: NaN }, { totalTracks: 4 }, { tracks: [entry(1), entry(1), entry(2)] }]) { const f = fixture({ getLoudnessStatus: async () => snapshot(patch) }); await f.controller.load(); assert.equal(f.controller.snapshot, null); assert.ok(f.controller.error); }
  const f = fixture({ previewLoudness: async () => preview([track(2)]) }); await f.controller.load(); f.controller.setSelection([id(1)]); await f.controller.requestPreview(); assert.equal(f.controller.preview, null); assert.equal(f.controller.canRun, false); assert.ok(f.controller.error);
  const g = fixture({ getLoudnessStatus: async () => { throw new Error('/Users/private/track.mp3'); } }); await g.controller.load(); assert.doesNotMatch(g.controller.error, /Users|private/);
});
test('external engine or enablement changes require refreshed status before another preview', async () => {
  for (const code of ['loudness_unavailable', 'loudness_disabled']) { const f = fixture({ previewLoudness: async () => { throw Object.assign(new Error('/private/engine'), { code }); } }); await f.controller.load(); f.controller.setSelection([id(1)]); await f.controller.requestPreview(); assert.equal(f.controller.statusFresh, false); assert.equal(f.controller.canPreview, false); assert.doesNotMatch(f.controller.error, /private/); }
});
test('late load or navigation-away preview cannot revive invalidated context or surface old failures', async () => {
  let finish; const f = fixture({ getLoudnessStatus: () => new Promise((resolve) => { finish = resolve; }) }); const pending = f.controller.load(); f.controller.invalidateContext(); finish(snapshot()); await pending; assert.equal(f.controller.snapshot, null); assert.equal(f.applied.length, 0);
  const g = fixture({ previewLoudness: () => new Promise((resolve) => { finish = resolve; }) }); await g.controller.load(); g.controller.setSelection([id(1)]); const work = g.controller.requestPreview(); g.leave(); finish(preview()); await work; assert.equal(g.controller.preview, null);
});
test('post-write warning preserves receipt counts and informational status but requires refresh', async () => {
  const warning = 'Conserva las copias de seguridad y actualiza el estado antes de continuar.'; const f = fixture({ runLoudness: async () => result({ warning }) }); await f.controller.load(); f.controller.setSelection([id(1)]); await f.controller.requestPreview(); await f.controller.run(); assert.equal(f.controller.result.changedCount, 1); assert.equal(f.controller.result.backupCount, 1); assert.equal(f.controller.result.warning, warning); assert.equal(f.controller.statusFresh, false); assert.equal(f.controller.canPreview, false); assert.equal(f.controller.preview, null); await f.controller.load(); assert.equal(f.controller.statusFresh, true);
});
test('malformed receipt warning cannot leak technical paths or discard completed mutation counts', async () => {
  const f = fixture({ runLoudness: async () => result({ warning: '/Users/private/cache.py: traceback' }) }); await f.controller.load(); f.controller.setSelection([id(1)]); await f.controller.requestPreview(); await f.controller.run(); assert.equal(f.controller.result.changedCount, 1); assert.doesNotMatch(f.controller.result.warning, /Users|traceback/); assert.equal(f.controller.statusFresh, false);
});
test('backup reveal sends no arguments and preserves current preview, settings draft and receipt', async () => {
  const requests = []; const f = fixture({ revealLoudnessBackups: async (...args) => { requests.push(args); return { found: true }; } }); await f.controller.load(); f.controller.setSelection([id(1)]); await f.controller.requestPreview(); const current = f.controller.preview; await f.controller.revealBackups(); assert.deepEqual(requests, [[]]); assert.equal(f.controller.preview, current); assert.match(f.controller.backupNotice, /abierta/); f.controller.setTarget(-12); const draft = f.controller.snapshot; const applied = f.applied.length; await f.controller.revealBackups(); assert.equal(f.controller.snapshot, draft); assert.equal(f.controller.dirty, true); assert.equal(f.applied.length, applied);
});
test('missing optional reveal API, empty backups, duplicate clicks and disconnect are harmless', async () => {
  const missing = fixture(); assert.equal(missing.controller.canRevealBackups, false); await missing.controller.revealBackups(); assert.equal(missing.calls.length, 0);
  let finish; let calls = 0; const f = fixture({ revealLoudnessBackups: () => { calls++; return new Promise((resolve) => { finish = resolve; }); } }); const pending = f.controller.revealBackups(); await f.controller.revealBackups(); assert.equal(f.controller.canRevealBackups, false); finish({ found: false }); await pending; assert.match(f.controller.backupNotice, /Todavía no hay copias/); assert.equal(calls, 1); f.disconnect(); await f.controller.revealBackups(); assert.equal(calls, 1);
});
test('reveal failure maps to safe Spanish and never returns a technical path', async () => {
  const f = fixture({ revealLoudnessBackups: async () => { throw new Error('/Users/private/loudness-backups'); } }); await f.controller.revealBackups(); assert.ok(f.controller.error); assert.doesNotMatch(f.controller.error, /Users|private|backups/);
});
