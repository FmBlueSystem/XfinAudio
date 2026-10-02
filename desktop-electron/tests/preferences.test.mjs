import assert from 'node:assert/strict';
import test from 'node:test';
import { PreferencesController } from '../.out/renderer/preferences.js';
const snapshot = (patch = {}) => ({ revision: 'a'.repeat(64), previewVolume: 0.8, watchLibrary: true, recoveryWarning: false, libraryLabels: ['Música DJ'], capabilities: { loudnessWriteback: false, providers: false, language: 'es' }, ...patch });
function fixture(overrides = {}) {
  const calls = []; const applied = []; const dirty = []; let busy = false; let route = 0;
  const api = { getPreferences: async () => { calls.push(['get']); return snapshot(); }, savePreferences: async (input) => { calls.push(['save', input]); return snapshot({ ...input, revision: 'b'.repeat(64) }); }, ...overrides };
  const controller = new PreferencesController(api, { canAct: () => !busy, changed: () => {}, dirtyChanged: (value) => dirty.push(value), applied: (value, reason) => applied.push([value, reason]), perform: async (_label, task, apply, failure) => { if (busy) return; busy = true; const start = route; try { apply(await task(), start === route); } catch (error) { failure(error); } finally { busy = false; } } });
  return { controller, calls, applied, dirty, leave: () => { route++; }, block: () => { busy = true; } };
}
test('loads real persistent snapshot and notifies host without writing or applying a local draft', async () => {
  const f = fixture(); await f.controller.load(); assert.equal(f.controller.snapshot.previewVolume, 0.8); assert.equal(f.controller.dirty, false); assert.deepEqual(f.calls, [['get']]); assert.equal(f.applied[0][1], 'load');
  f.controller.setVolume(0.35); f.controller.setWatchLibrary(false); assert.equal(f.controller.dirty, true); assert.equal(f.applied.length, 1); assert.deepEqual(f.calls, [['get']]); assert.equal(f.dirty.at(-1), true);
});
test('dirty navigation and refresh preserve draft until explicit local discard', async () => {
  const f = fixture(); await f.controller.load(); f.controller.setVolume(0.4); f.leave(); await f.controller.load(); assert.equal(f.controller.snapshot.previewVolume, 0.4); assert.equal(f.controller.dirty, true); assert.deepEqual(f.calls, [['get']]); assert.match(f.controller.error, /descarta/i);
  f.controller.discard(); assert.equal(f.controller.snapshot.previewVolume, 0.8); assert.equal(f.controller.dirty, false); assert.equal(f.calls.length, 1); assert.equal(f.applied.length, 1); await f.controller.load(); assert.equal(f.calls.length, 2);
});
test('explicit save sends only revision, finite preview volume and boolean watch, accepting result after navigation', async () => {
  let finish; const writes = []; const f = fixture({ savePreferences: (input) => { writes.push(input); return new Promise((resolve) => { finish = resolve; }); } }); await f.controller.load(); f.controller.setVolume(0); f.controller.setWatchLibrary(false); const pending = f.controller.save(); f.leave(); finish(snapshot({ revision: 'b'.repeat(64), previewVolume: 0, watchLibrary: false })); await pending;
  assert.deepEqual(writes, [{ revision: 'a'.repeat(64), previewVolume: 0, watchLibrary: false }]); assert.equal(f.controller.dirty, false); assert.equal(f.controller.snapshot.revision, 'b'.repeat(64)); assert.equal(f.applied.at(-1)[1], 'save');
});
test('stale save preserves draft and blocks repetition until discard then refresh loads a new revision', async () => {
  let refreshed = false; const f = fixture({ getPreferences: async () => snapshot({ revision: refreshed ? 'c'.repeat(64) : 'a'.repeat(64), previewVolume: refreshed ? 0.2 : 0.8 }), savePreferences: async () => { throw new Error("Error invoking remote method: [stale_settings] /Users/private/settings.json"); } }); await f.controller.load(); f.controller.setVolume(0.6); await f.controller.save(); assert.equal(f.controller.snapshot.previewVolume, 0.6); assert.equal(f.controller.dirty, true); assert.equal(f.controller.canSave, false); assert.match(f.controller.error, /descarta.*actualiza/i); assert.doesNotMatch(f.controller.error, /remote method|Users|stale_settings/);
  f.controller.discard(); assert.equal(f.controller.dirty, false); refreshed = true; await f.controller.load(); assert.equal(f.controller.snapshot.revision, 'c'.repeat(64)); assert.equal(f.controller.snapshot.previewVolume, 0.2); f.controller.setVolume(0.3); assert.equal(f.controller.canSave, true);
});
test('invalid edits are rejected and no unsupported fields or service activation are sent', async () => {
  const f = fixture(); await f.controller.load(); for (const value of [NaN, Infinity, -0.1, 1.1, '0.5', null]) f.controller.setVolume(value); for (const value of [1, 'true', null]) f.controller.setWatchLibrary(value); assert.equal(f.controller.snapshot.previewVolume, 0.8); assert.equal(f.controller.snapshot.watchLibrary, true); assert.equal(f.controller.dirty, false);
  f.controller.setVolume(1); await f.controller.save(); assert.deepEqual(Object.keys(f.calls.at(-1)[1]).sort(), ['previewVolume', 'revision', 'watchLibrary']); assert.deepEqual(f.controller.snapshot.capabilities, { loudnessWriteback: false, providers: false, language: 'es' });
});
test('pending operation rejects duplicate saves and local edits/discard while preserving dirty state on failure', async () => {
  let reject; let saves = 0; const f = fixture({ savePreferences: () => { saves++; return new Promise((_resolve, fail) => { reject = fail; }); } }); await f.controller.load(); f.controller.setVolume(0.3); const pending = f.controller.save(); await f.controller.save(); f.controller.setVolume(0.9); f.controller.discard(); assert.equal(f.controller.pending, true); assert.equal(f.controller.snapshot.previewVolume, 0.3); reject(new Error('/secret/location')); await pending; assert.equal(saves, 1); assert.equal(f.controller.dirty, true); assert.equal(f.controller.pending, false); assert.doesNotMatch(f.controller.error, /secret/);
});
test('offline preferences stay visible and edits/save/load/discard respect global gate', async () => {
  const f = fixture(); await f.controller.load(); f.controller.setVolume(0.4); f.block(); f.controller.setWatchLibrary(false); f.controller.discard(); await f.controller.save(); await f.controller.load(); assert.equal(f.controller.snapshot.previewVolume, 0.4); assert.equal(f.controller.snapshot.watchLibrary, true); assert.equal(f.controller.dirty, true); assert.equal(f.calls.length, 1);
});
test('snapshot copies isolate backend objects and malformed results fail safely', async () => {
  const original = snapshot(); const f = fixture({ getPreferences: async () => original }); await f.controller.load(); original.previewVolume = 0.01; original.libraryLabels.push('Later'); assert.equal(f.controller.snapshot.previewVolume, 0.8); assert.deepEqual(f.controller.snapshot.libraryLabels, ['Música DJ']);
  for (const patch of [{ previewVolume: NaN }, { watchLibrary: 'true' }, { revision: 'bad' }]) { const g = fixture({ getPreferences: async () => snapshot(patch) }); await g.controller.load(); assert.equal(g.controller.snapshot, null); assert.equal(g.applied.length, 0); assert.ok(g.controller.error); }
});
test('implemented loudness capability is reported without activating provider capabilities', async () => {
  const f = fixture({ getPreferences: async () => snapshot({ capabilities: { loudnessWriteback: true, providers: false, language: 'es' } }) }); await f.controller.load(); assert.equal(f.controller.snapshot?.capabilities.loudnessWriteback, true); assert.equal(f.controller.snapshot.capabilities.providers, false); assert.equal(f.controller.error, '');
});
test('optional provider capability is truthful without automatically enabling or contacting it', async () => { const f=fixture({getPreferences:async()=>snapshot({capabilities:{loudnessWriteback:true,providers:true,language:'es'}})});await f.controller.load();assert.equal(f.controller.snapshot?.capabilities.providers,true);assert.deepEqual(f.calls,[]);});
test('library-label refresh updates only metadata, preserving dirty settings, original revision and playback application',async()=>{
 let current=snapshot({libraryLabels:[]});const f=fixture({getPreferences:async()=>current});await f.controller.load();f.controller.setVolume(.4);f.controller.setWatchLibrary(false);
 current=snapshot({revision:'c'.repeat(64),previewVolume:.1,libraryLabels:['music']});await f.controller.refreshLibraryLabels();
 assert.deepEqual(f.controller.snapshot.libraryLabels,['music']);assert.equal(f.controller.snapshot.previewVolume,.4);assert.equal(f.controller.snapshot.watchLibrary,false);assert.equal(f.controller.snapshot.revision,'a'.repeat(64));assert.equal(f.controller.dirty,true);assert.equal(f.applied.length,1);
 f.controller.discard();assert.deepEqual(f.controller.snapshot.libraryLabels,['music']);assert.equal(f.controller.snapshot.previewVolume,.8);assert.equal(f.controller.snapshot.revision,'a'.repeat(64));assert.equal(f.applied.length,1);
});
test('metadata-only preference refresh preserves conflict and rejects malformed results without mutating labels',async()=>{
 let current=snapshot();const f=fixture({getPreferences:async()=>current,savePreferences:async()=>{throw Error('[stale_settings]');}});await f.controller.load();f.controller.setVolume(.4);await f.controller.save();const error=f.controller.error;
 current=snapshot({libraryLabels:['new']});await f.controller.refreshLibraryLabels();assert.equal(f.controller.canSave,false);assert.equal(f.controller.error,error);assert.equal(f.applied.length,1);
 current={...current,revision:'invalid'};await f.controller.refreshLibraryLabels();assert.deepEqual(f.controller.snapshot.libraryLabels,['new']);assert.equal(f.controller.snapshot.previewVolume,.4);assert.equal(f.controller.canSave,false);
});
