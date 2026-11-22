import assert from 'node:assert/strict';
import test from 'node:test';
import { createRequire } from 'node:module';
import { SeratoExportController, crateTreeLines, parentCrateLabel, phaseReasonLine } from '../.out/renderer/serato-export.js';
const require = createRequire(import.meta.url);
const source = { kind: 'review', reviewId: 'review-1' };
const destination = { destinationId: 'destination-1', label: 'Subcrates · Disco DJ' };
const preview = (patch = {}) => ({ previewId: 'preview-1', sourceRevision: 'revision-1', filename: 'Mi sesión.crate', destinationLabel: destination.label, trackCount: 2, readiness: 'needs_review', warnings: ['Revisa la transición'], blockers: [], canCommit: true, tracks: [{ id: 'a', title: 'A', artist: 'Artista' }, { id: 'b', title: 'B', artist: 'Artista' }], backup: { required: true }, ...patch });
const receipt = { receiptId: 'receipt-1', filename: 'Mi sesión.crate', destinationLabel: destination.label, trackCount: 2, validated: true, backupCreated: true };
const detected = { destinationId: 'detected-1', label: '_Serato_ · dd' };
const flush = () => new Promise((resolve) => setTimeout(resolve, 0));
function fixture(overrides = {}) {
  const calls = []; let busy = false; let revision = 0;
  const api = { chooseSeratoDestination: async () => { calls.push(['choose']); return destination; }, previewSeratoExport: async (input) => { calls.push(['preview', input]); return preview(); }, commitSeratoExport: async (input) => { calls.push(['commit', input]); return receipt; }, revealSeratoExport: async (input) => { calls.push(['reveal', input]); }, ...overrides };
  const controller = new SeratoExportController(api, { canAct: () => !busy, changed: () => {}, perform: async (_label, task, apply, failure) => { if (busy) return; busy = true; const started = revision; try { apply(await task(), started === revision); } catch (error) { failure(error); } finally { busy = false; } } });
  return { controller, calls, leave: () => { revision++; }, busy: () => { busy = true; }, ready: async () => { controller.setSource(source, '  Mi sesión  '); await controller.chooseDestination(); await controller.requestPreview(); } };
}
test('parent crate names read with Serato nesting shown as › to the user', () => {
  assert.equal(parentCrateLabel('XfinAudio%%Metadata'), 'XfinAudio › Metadata');
  assert.equal(parentCrateLabel('XfinAudio%%Metadata%%Pendientes'), 'XfinAudio › Metadata › Pendientes');
  assert.equal(parentCrateLabel('XfinAudio'), 'XfinAudio');
});
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

test('a source is previewed from an automatically detected destination without any picker',async()=>{
 let detections=0;const f=fixture({detectSeratoDestination:async()=>{detections++;return detected;}});
 f.controller.setSource(source,'Mi sesión');await flush();
 assert.equal(detections,1,'the export screen must detect the destination on its own');
 assert.deepEqual(f.controller.destination,detected);assert.equal(f.controller.destinationDetected,true);assert.equal(f.controller.detectionMissed,false);
 assert.deepEqual(f.calls.filter(([op])=>op==='choose'),[],'detection must never open the native picker');
 assert.equal(f.controller.canPreview,true);await f.controller.requestPreview();
 assert.equal(f.calls.at(-1)[1].destinationId,detected.destinationId);
 assert.equal(f.controller.preview.destinationLabel,destination.label);
});

test('a detection that finds nothing says so in Spanish and waits for the manual choice',async()=>{
 let detections=0;const f=fixture({detectSeratoDestination:async()=>{detections++;return null;}});
 f.controller.setSource(source,'Mi sesión');await flush();
 assert.equal(detections,1);assert.equal(f.controller.destination,null);assert.equal(f.controller.destinationDetected,false);
 assert.equal(f.controller.detectionMissed,true,'a miss must be visible instead of silently opening the dialog');
 assert.deepEqual(f.calls,[],'a miss must not open the native picker on its own');assert.equal(f.controller.error,'');
 await f.controller.chooseDestination();
 assert.deepEqual(f.calls,[['choose']],'the manual choice stays available after a miss');
 assert.deepEqual(f.controller.destination,destination);assert.equal(f.controller.detectionMissed,false);assert.equal(f.controller.destinationDetected,false);
});

test('detection errors keep the manual path with safe Spanish guidance',async()=>{
 const f=fixture({detectSeratoDestination:async()=>{throw new Error("Error invoking remote method 'detectSeratoDestination': [core_stopped] /Volumes/dd");}});
 f.controller.setSource(source,'Mi sesión');await flush();
 assert.equal(f.controller.destination,null);assert.equal(f.controller.error.includes('core_stopped'),false);assert.match(f.controller.error,/Reinicia XfinAudio/);
 await f.controller.chooseDestination();assert.deepEqual(f.calls,[['choose']]);assert.equal(f.controller.error,'');
});

test('a destination the user already chose is never replaced by automatic detection',async()=>{
 let detections=0;const f=fixture({detectSeratoDestination:async()=>{detections++;return detected;}});
 await f.controller.chooseDestination();f.controller.setSource({kind:'saved',playlistId:'2'},'Otra');await flush();
 assert.equal(detections,0,'a manual choice must keep winning over detection');assert.deepEqual(f.controller.destination,destination);
});

test('a core stop drops the destination and preview but keeps the source and crate name',async()=>{
 let detections=0;const f=fixture({detectSeratoDestination:async()=>{detections++;return detected;}});
 f.controller.setSource(source,'Mi sesión');await flush();
 assert.deepEqual(f.controller.destination,detected);await f.controller.requestPreview();assert.ok(f.controller.preview);
 f.controller.forgetCore();
 assert.equal(f.controller.destination,null);assert.equal(f.controller.preview,null);
 assert.equal(f.controller.destinationDetected,false);assert.equal(f.controller.detectionMissed,false);
 assert.deepEqual(f.controller.source,source);assert.equal(f.controller.name,'Mi sesión');
 assert.equal(f.controller.error,'');
 f.controller.setSource(source,'Mi sesión');await flush();
 assert.equal(detections,2,'using the page again detects the folder again');
 assert.deepEqual(f.controller.destination,detected);assert.equal(f.controller.canPreview,true);
});

test('a preview whose destination id a restarted core forgot shows the not-found path, not a folder refusal',async()=>{
 const f=fixture({detectSeratoDestination:async()=>detected,previewSeratoExport:async(input)=>{f.calls.push(['preview',input]);throw new Error("Error invoking remote method 'xfin:action': [unknown_destination] Local export unavailable");}});
 f.controller.setSource(source,'Mi sesión');await flush();await f.controller.requestPreview();
 assert.equal(f.controller.destination,null);assert.equal(f.controller.detectionMissed,true);
 assert.equal(f.controller.preview,null);assert.equal(f.controller.error,'','the user is never asked to choose a folder detection can find');
 assert.equal(f.calls.filter(([operation])=>operation==='preview').length,1);
});
test('a generated set leaves the crate name to the core while a typed name is sent unchanged', async () => {
  const f = fixture();
  f.controller.setSource(source, '');
  await f.controller.chooseDestination();
  assert.equal(f.controller.canPreview, true, 'an empty name is the automatic name of a generated set');
  await f.controller.requestPreview();
  assert.deepEqual(f.calls.at(-1), ['preview', { source, destinationId: destination.destinationId }], 'no name travels, so the core proposes one from the style and the date');
  f.controller.setName('Mi sesión');
  await f.controller.requestPreview();
  assert.deepEqual(f.calls.at(-1), ['preview', { source, destinationId: destination.destinationId, name: 'Mi sesión' }], 'a name the user types is used unchanged');
  f.controller.setSource({ kind: 'saved', playlistId: 'playlist-1' }, '');
  assert.equal(f.controller.canPreview, false, 'a saved playlist still needs its own name to preview');
});
test('the page shows the crate name the core chose for a generated set', async () => {
  const chosen = 'XfinAudio%%Build 6-jun.crate';
  const f = fixture({
    previewSeratoExport: async () => preview({ filename: chosen }),
    commitSeratoExport: async (input) => { f.calls.push(['commit', input]); return { ...receipt, filename: chosen }; },
  });
  f.controller.setSource(source, ''); await f.controller.chooseDestination(); await f.controller.requestPreview();
  assert.equal(f.controller.preview.filename, 'XfinAudio%%Build 6-jun.crate');
  assert.equal(f.controller.canCommit, true);
  await f.controller.commit();
  assert.equal(f.controller.receipt.filename, chosen, 'the receipt keeps the exported crate name');
});
test('a commit refused because Serato DJ is open keeps the preview so the user can confirm again (S13)', async () => {
  let open = true;
  const f = fixture({ commitSeratoExport: async (input) => { f.calls.push(['commit', input]); if (open) throw new Error("Error invoking remote method 'xfin:action': [serato_running] Close Serato DJ"); return receipt; } }); await f.ready();
  const previous = f.controller.preview; await f.controller.commit();
  assert.equal(f.controller.preview, previous); assert.equal(f.controller.canCommit, true); assert.equal(f.controller.receipt, null);
  assert.match(f.controller.error, /^Cierra Serato DJ antes de exportar\./); assert.doesNotMatch(f.controller.status, /No se pudo confirmar/);
  open = false; await f.controller.commit(); assert.deepEqual(f.controller.receipt, receipt); assert.equal(f.calls.filter(([operation]) => operation === 'commit').length, 2);
});

test('a split travels as segmentSize for that one export and is forgotten afterwards (S1)', async () => {
  const f = fixture(); await f.ready();
  assert.deepEqual(f.calls.at(-1), ['preview', { source, destinationId: destination.destinationId, name: 'Mi sesión' }], 'no split keeps today\'s preview request byte for byte');
  assert.equal(f.controller.segmentSize, null);
  f.controller.setSegmentSize(5);
  assert.equal(f.controller.preview, null, 'changing the split invalidates the preview');
  await f.controller.requestPreview();
  assert.deepEqual(f.calls.at(-1), ['preview', { source, destinationId: destination.destinationId, name: 'Mi sesión', segmentSize: 5 }]);
  assert.deepEqual(f.controller.preview, preview(), 'the receipt keeps the crate the core planned');
  for (const invalid of [1, 51, 0, -2, 2.5, NaN, Infinity, '5', true]) { f.controller.setSegmentSize(invalid); assert.equal(f.controller.segmentSize, 5, `${String(invalid)} is not a valid tramo`); }
  for (const accepted of [2, 3, 49, 50]) { f.controller.setSegmentSize(accepted); assert.equal(f.controller.segmentSize, accepted); }
  f.controller.setSegmentSize(null); assert.equal(f.controller.segmentSize, null, 'no dividir is the single crate again');
  f.controller.setSegmentSize(4); await f.controller.requestPreview(); await f.controller.commit();
  assert.equal(f.controller.segmentSize, null, 'the split applies to that export only');
  f.controller.setSegmentSize(4); f.controller.setSource({ kind: 'saved', playlistId: '2' }, 'Otra');
  assert.equal(f.controller.segmentSize, null, 'a new export starts with today\'s single crate');
});
test('phases travel as splitMode for that one export, ignoring and then forgetting the tramo size (S4)', async () => {
  const f = fixture(); await f.ready();
  f.controller.setSplitMode('phases');
  assert.equal(f.controller.splitMode, 'phases');
  assert.equal(f.controller.preview, null, 'choosing phases invalidates the preview');
  await f.controller.requestPreview();
  assert.deepEqual(f.calls.at(-1), ['preview', { source, destinationId: destination.destinationId, name: 'Mi sesión', splitMode: 'phases' }], 'phases send only the mode, never a tramo size');
  f.controller.setSegmentSize(5); await f.controller.requestPreview();
  assert.deepEqual(f.calls.at(-1), ['preview', { source, destinationId: destination.destinationId, name: 'Mi sesión', segmentSize: 5 }], 'going back to every N tracks sends the size alone, exactly as before');
  f.controller.setSplitMode('phases'); await f.controller.requestPreview();
  assert.deepEqual(f.calls.at(-1)[1].splitMode, 'phases');
  assert.equal('segmentSize' in f.calls.at(-1)[1], false, 'the tramo size typed earlier is not sent in phases mode');
  await f.controller.commit();
  assert.equal(f.controller.splitMode, 'none', 'the choice belongs to that export only');
  assert.equal(f.controller.segmentSize, null);
  f.controller.setSplitMode('phases'); f.controller.setSource({ kind: 'saved', playlistId: '2' }, 'Otra');
  assert.equal(f.controller.splitMode, 'none', 'a new export starts on today\'s single crate');
  f.controller.setSplitMode('phases'); f.controller.setSplitMode('none');
  assert.equal(f.controller.splitMode, 'none', 'no dividir is available again');
});
test('a metadata worklist never holds a phases split', async () => {
  const f = fixture();
  f.controller.setSource({ kind: 'metadata', status: 'incomplete', missingField: 'bpm', trackIds: ['a'.repeat(64)] }, 'Reparar BPM');
  await f.controller.chooseDestination();
  f.controller.setSplitMode('phases');
  assert.equal(f.controller.splitMode, 'none', 'the core refuses phases with a metadata worklist');
  await f.controller.requestPreview();
  assert.equal('splitMode' in f.calls.at(-1)[1], false);
});
test('a reason the screen does not know is never invented', () => {
  assert.equal(phaseReasonLine(undefined), '');
  assert.equal(phaseReasonLine('flat'), 'La energía de la lista es casi pareja; no hay fases claras y se exportará sin dividir.');
  assert.equal(phaseReasonLine('unknown_from_a_newer_core'), '');
});
test('a tree receipt status says how many crates were written (S6)', async () => {
  const files = [{ name: 'XfinAudio%%Sesión 14-nov.crate', trackCount: 12 }, { name: 'XfinAudio%%Sesión 14-nov%%1 (1-5).crate', trackCount: 5 }, { name: 'XfinAudio%%Sesión 14-nov%%3 (11-12).crate', trackCount: 2 }];
  const f = fixture({ commitSeratoExport: async (input) => { f.calls.push(['commit', input]); return { ...receipt, filename: files[0].name, files }; } });
  await f.ready(); await f.controller.commit();
  assert.equal(f.controller.status, 'Árbol exportado a Serato: 3 crates', 'the receipt names the whole tree at once');
  const single = fixture({ commitSeratoExport: async () => ({ ...receipt, files: [] }) }); await single.ready(); await single.controller.commit();
  assert.equal(single.controller.status, 'Crate exportado y validado: Mi sesión.crate', 'a receipt without a tree reads exactly as before');
  const unchanged = fixture(); await unchanged.ready(); await unchanged.controller.commit();
  assert.equal(unchanged.controller.status, 'Crate exportado y validado: Mi sesión.crate', 'a receipt without the new field reads exactly as before');
});
test('the page and the native dialog phrase a crate tree identically (S4)', async () => {
  const { crateTreeLines: nativeLines } = require('../.out/main/serato-host.js');
  const crates = [{ name: 'XfinAudio%%Sesión 14-nov.crate', trackCount: 20, action: 'create' }, { name: 'XfinAudio%%Sesión 14-nov%%1 (1-5).crate', trackCount: 5, action: 'replace' }];
  assert.deepEqual(crateTreeLines(crates), nativeLines(crates), 'the two Spanish copies must not drift');
  assert.deepEqual(crateTreeLines(undefined), []); assert.deepEqual(crateTreeLines([]), []);
});

test('a metadata worklist never holds a tramo size', async () => {
  const f = fixture();
  f.controller.setSource({ kind: 'metadata', status: 'incomplete', missingField: 'bpm', trackIds: ['a'.repeat(64)] }, 'Reparar BPM');
  await f.controller.chooseDestination();
  f.controller.setSegmentSize(5);
  assert.equal(f.controller.segmentSize, null, 'the core refuses a tramo size with a metadata worklist');
  await f.controller.requestPreview();
  assert.equal('segmentSize' in f.calls.at(-1)[1], false);
});
test('a typed name is bounded by the crate file the core really writes, prefix included', async () => {
  // The core nests every typed name under the XfinAudio parent crate, so the 240-byte cap
  // applies to `XfinAudio%%<name>.crate` (11 + name + 6 bytes): the typed name keeps only
  // the remaining budget, and a name that already carries the prefix is not doubled.
  const f = fixture(); await f.ready();
  for (const name of ['é'.repeat(111), `XfinAudio%%${'é'.repeat(111)}`]) {
    f.controller.setName(name);
    assert.equal(f.controller.canPreview, true, `${name.length} characters fit the 240-byte crate file`);
  }
  for (const name of ['é'.repeat(112), `XfinAudio%%${'é'.repeat(112)}`]) {
    f.controller.setName(name);
    assert.equal(f.controller.canPreview, false, `${name.length} characters do not fit the 240-byte crate file`);
  }
});
