import assert from 'node:assert/strict';
import test from 'node:test';
import { SeratoExportController } from '../.out/renderer/serato-export.js';
const source = { kind: 'review', reviewId: 'review-1' };
const destination = { destinationId: 'destination-1', label: 'Subcrates · Disco DJ' };
const preview = (patch = {}) => ({ previewId: 'preview-1', sourceRevision: 'revision-1', filename: 'Mi sesión.crate', destinationLabel: destination.label, trackCount: 2, readiness: 'needs_review', warnings: ['Revisa la transición'], blockers: [], canCommit: true, tracks: [{ id: 'a', title: 'A', artist: 'Artista' }, { id: 'b', title: 'B', artist: 'Artista' }], backup: { required: true }, ...patch });
const receipt = { receiptId: 'receipt-1', filename: 'Mi sesión.crate', destinationLabel: destination.label, trackCount: 2, validated: true, backupCreated: true };
function fixture(overrides = {}) {
  const calls = []; let busy = false; let revision = 0;
  const api = { chooseSeratoDestination: async () => { calls.push(['choose']); return destination; }, previewSeratoExport: async (input) => { calls.push(['preview', input]); return preview(); }, commitSeratoExport: async (input) => { calls.push(['commit', input]); return receipt; }, revealSeratoExport: async (input) => { calls.push(['reveal', input]); }, ...overrides };
  const controller = new SeratoExportController(api, { canAct: () => !busy, changed: () => {}, perform: async (_label, task, apply, failure) => { if (busy) return; busy = true; const started = revision; try { apply(await task(), started === revision); } catch (error) { failure(error); } finally { busy = false; } } });
  return { controller, calls, leave: () => { revision++; }, busy: () => { busy = true; }, ready: async () => { controller.setSource(source, '  Mi sesión  '); await controller.chooseDestination(); await controller.requestPreview(); } };
}
test('preview and export are separate explicit actions with no paths, bytes or confirmation flags', async () => {
  const f = fixture(); await f.controller.requestPreview(); await f.controller.commit(); assert.deepEqual(f.calls, []); await f.ready();
  assert.deepEqual(f.calls, [['choose'], ['preview', { source, destinationId: destination.destinationId, name: 'Mi sesión' }]]); assert.equal(f.controller.canCommit, true); assert.equal(f.controller.receipt, null);
  await f.controller.commit(); assert.deepEqual(f.calls.at(-1), ['commit', { previewId: 'preview-1' }]); assert.deepEqual(f.controller.receipt, receipt); assert.equal(f.controller.preview, null); await f.controller.commit(); assert.equal(f.calls.length, 3);
});
test('saved source is copied as identity only and exports the saved revision', async () => {
  const f = fixture(); const input = { kind: 'saved', playlistId: 'playlist-1', path: '/private/file' }; f.controller.setSource(input, 'Guardada'); input.playlistId = 'changed'; await f.controller.chooseDestination(); await f.controller.requestPreview();
  assert.deepEqual(f.calls.at(-1)[1].source, { kind: 'saved', playlistId: 'playlist-1' }); assert.equal(f.controller.preview.sourceRevision, 'revision-1');
});
test('source and name changes invalidate preview; invalid names cannot preview', async () => {
  const f = fixture(); await f.ready(); f.controller.setName('Nueva'); assert.equal(f.controller.preview, null); await f.controller.requestPreview(); f.controller.setSource({ kind: 'saved', playlistId: 'playlist-1' }, 'Guardada'); assert.equal(f.controller.preview, null);
  for (const name of ['', '  ', '.', '..', 'x/y', 'x\\y', 'x:y', '\u200bhidden', 'é'.repeat(120), 'bad\nname', 'bad\0name', 'x'.repeat(201)]) { f.controller.setName(name); assert.equal(f.controller.canPreview, false); const count = f.calls.length; await f.controller.requestPreview(); assert.equal(f.calls.length, count); }
});
test('picker cancellation is harmless while an actual destination change invalidates preview', async () => {
  let next = destination; const f = fixture({ chooseSeratoDestination: async () => next }); await f.ready(); const previous = f.controller.preview; next = null; await f.controller.chooseDestination(); assert.equal(f.controller.preview, previous); assert.deepEqual(f.controller.destination, destination);
  next = { destinationId: 'other', label: 'Otra carpeta' }; await f.controller.chooseDestination(); assert.equal(f.controller.preview, null); assert.equal(f.controller.destination.destinationId, 'other');
});
test('late previews cannot revive changed source, name, invalidation or departed route', async () => {
  for (const change of [(f) => f.controller.setName('Nueva'), (f) => f.controller.setSource({ kind: 'saved', playlistId: '2' }, 'Otra'), (f) => f.controller.invalidatePreview(), (f) => f.leave()]) {
    let finish; const f = fixture({ previewSeratoExport: () => new Promise((resolve) => { finish = resolve; }) }); f.controller.setSource(source, 'Nombre'); await f.controller.chooseDestination(); const pending = f.controller.requestPreview(); change(f); finish(preview()); await pending; assert.equal(f.controller.preview, null); assert.equal(f.controller.canCommit, false);
  }
});
test('late destination picker cannot overwrite a newer source context', async () => {
  let finish; const f = fixture({ chooseSeratoDestination: () => new Promise((resolve) => { finish = resolve; }) }); f.controller.setSource(source, 'Nombre'); const choosing = f.controller.chooseDestination(); f.controller.setSource({ kind: 'saved', playlistId: '2' }, 'Otra'); finish(destination); await choosing; assert.equal(f.controller.destination, null);
});
test('hard blockers, empty preview and canCommit false block writes but needs_review remains eligible', async () => {
  for (const patch of [{ readiness: 'blocked' }, { blockers: ['Falta una pista'] }, { canCommit: false }, { tracks: [] }, { trackCount: 0 }, { previewId: '' }]) { const f = fixture({ previewSeratoExport: async () => preview(patch) }); await f.ready(); assert.equal(f.controller.canCommit, false); await f.controller.commit(); assert.equal(f.calls.some(([operation]) => operation === 'commit'), false); }
  const f = fixture(); await f.ready(); assert.equal(f.controller.canCommit, true);
});
test('pending commit blocks repeat export and retains actual receipt after navigation/context changes', async () => {
  let finish; let calls = 0; const f = fixture({ commitSeratoExport: () => { calls++; return new Promise((resolve) => { finish = resolve; }); } }); await f.ready(); const pending = f.controller.commit(); assert.equal(f.controller.pending, 'commit'); await f.controller.commit(); f.leave(); f.controller.setSource({ kind: 'saved', playlistId: '2' }, 'Nueva'); f.controller.invalidatePreview(); finish(receipt); await pending;
  assert.equal(calls, 1); assert.deepEqual(f.controller.receipt, receipt); assert.equal(f.controller.pending, null); assert.equal(f.controller.source.playlistId, '2'); assert.match(f.controller.status, /exportad|validado/i);
});
test('native final confirmation cancellation preserves preview without a false receipt', async () => {
  const f = fixture({ commitSeratoExport: async () => ({ cancelled: true }) }); await f.ready(); const previous = f.controller.preview; await f.controller.commit(); assert.equal(f.controller.preview, previous); assert.equal(f.controller.receipt, null); assert.equal(f.controller.canCommit, true); assert.match(f.controller.status, /cancelada/i);
});
test('caught errors show safe Spanish guidance, consume failed commit preview, and keep previous receipts', async () => {
  const f = fixture({ commitSeratoExport: async () => { throw new Error("Error invoking remote method 'serato:commit': [stale_export] /Users/private/DJ.crate"); } }); await f.ready(); await f.controller.commit(); assert.equal(f.controller.preview, null); assert.match(f.controller.error, /vista previa/); assert.doesNotMatch(f.controller.error, /remote method|Users|stale_export/);
  const g = fixture({ previewSeratoExport: async () => { throw new Error('/secret/path'); } }); await g.ready(); assert.doesNotMatch(g.controller.error, /secret/); assert.equal(g.controller.preview, null);
});
test('reveal uses only a verified receipt identity and respects the shared busy gate', async () => {
  const f = fixture(); await f.controller.reveal(); assert.deepEqual(f.calls, []); await f.ready(); await f.controller.commit(); f.controller.setSource(null); assert.deepEqual(f.controller.receipt, receipt); await f.controller.reveal(); assert.deepEqual(f.calls.at(-1), ['reveal', { receiptId: 'receipt-1' }]); f.busy(); const count = f.calls.length; await f.controller.reveal(); assert.equal(f.calls.length, count);
});


test('metadata worklist source is copied exactly and cannot be changed through caller arrays',async()=>{
 const f=fixture(),ids=['a'.repeat(64),'b'.repeat(64)],chosen={kind:'metadata',status:'incomplete',missingField:'bpm',trackIds:ids};
 f.controller.setSource(chosen,'Repair');ids.pop();await f.controller.chooseDestination();await f.controller.requestPreview();
 const input=f.calls.find(([op])=>op==='preview')[1];assert.deepEqual(input.source,{kind:'metadata',status:'incomplete',missingField:'bpm',trackIds:['a'.repeat(64),'b'.repeat(64)]});
 assert.equal(f.controller.canCommit,true);
});
