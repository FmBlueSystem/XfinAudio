import assert from 'node:assert/strict';
import test from 'node:test';
import { LiveController, LiveElapsedClock } from '../.out/renderer/live.js';
const track = (id) => ({ id, title: `Pista ${id}`, artist: 'Artista', bpm: 120, key: '8A', energy: 5, duration: 180 });
const snapshot = (patch = {}) => ({ sessionId: 'session-1', revision: 1, sourceReviewId: 'review-1', state: 'active', current: track('a'), history: [], candidates: [{ track: track('b'), score: 0.84, alerts: ['Revisa el cambio'] }, { track: track('c'), score: 0.73, alerts: [] }], elapsedSeconds: 12, ...patch });
function fixture(overrides = {}) {
  const calls = []; let busy = false; let revision = 0;
  const api = { openLive: async (input) => { calls.push(['open', input]); return snapshot({ sourceReviewId: input.reviewId }); }, getLiveStatus: async (input) => { calls.push(['status', input]); return snapshot({ elapsedSeconds: 20 }); }, advanceLive: async (input) => { calls.push(['advance', input]); return snapshot({ revision: 2, current: track(input.trackId), history: [{ track: track('a'), startedAt: '2026-10-01T10:00:00Z' }], candidates: [{ track: track('c'), score: 0.92, alerts: [] }], elapsedSeconds: 0 }); }, clearLive: async (input) => { calls.push(['clear', input]); return { cleared: true }; }, ...overrides };
  const controller = new LiveController(api, { canAct: () => !busy, changed: () => {}, perform: async (_label, task, apply, failure) => { if (busy) return; busy = true; const start = revision; try { apply(await task(), start === revision); } catch (error) { failure(error); } finally { busy = false; } } });
  return { controller, calls, leave: () => { revision++; }, block: () => { busy = true; } };
}
test('opening Live supplies only reviewed identity and reopening preserves backend progress', async () => {
  let state = snapshot(); const f = fixture({ openLive: async () => state }); await f.controller.start('review-1'); state = snapshot({ revision: 4, current: track('c'), history: [{ track: track('a'), startedAt: '2026-10-01T10:00:00Z' }] }); await f.controller.start('review-1');
  assert.deepEqual(f.controller.snapshot, state); assert.equal(f.controller.snapshot.revision, 4);
  const g = fixture(); await g.controller.start('review-1'); assert.deepEqual(g.calls, [['open', { reviewId: 'review-1' }]]); assert.equal(g.controller.valid, true);
});
test('advance only sends a currently ranked opaque track and exact session revision, without playback', async () => {
  const f = fixture(); await f.controller.start('review-1'); await f.controller.advance('forged'); assert.equal(f.calls.length, 1); await f.controller.advance('b');
  assert.deepEqual(f.calls.at(-1), ['advance', { sessionId: 'session-1', revision: 1, trackId: 'b' }]); assert.equal(f.controller.snapshot.current.id, 'b'); assert.equal(f.controller.snapshot.history[0].track.id, 'a'); await f.controller.advance('b'); assert.equal(f.calls.length, 2);
});
test('refresh uses the current session and clear is explicit, leaving no fallback suggestions', async () => {
  const f = fixture(); await f.controller.refresh(); await f.controller.clear(); assert.deepEqual(f.calls, []); await f.controller.start('review-1'); await f.controller.refresh(); assert.deepEqual(f.calls.at(-1), ['status', { sessionId: 'session-1' }]); assert.equal(f.controller.snapshot.elapsedSeconds, 20); await f.controller.clear(); assert.deepEqual(f.calls.at(-1), ['clear', { sessionId: 'session-1' }]); assert.equal(f.controller.snapshot, null); assert.equal(f.controller.valid, false);
});
test('opening and advancing survive navigation without forcing navigation or losing progress', async () => {
  let finish; const f = fixture({ openLive: () => new Promise((resolve) => { finish = resolve; }) }); const request = f.controller.start('review-1'); f.leave(); finish(snapshot()); await request; assert.ok(f.controller.snapshot);
  let advance; const g = fixture({ advanceLive: () => new Promise((resolve) => { advance = resolve; }) }); await g.controller.start('review-1'); const next = g.controller.advance('b'); g.leave(); advance(snapshot({ revision: 2, current: track('b') })); await next; assert.equal(g.controller.snapshot.current.id, 'b');
});
test('explicit invalidation rejects late opening, refresh, advance and clear completions', async () => {
  for (const method of ['start', 'refresh', 'advance', 'clear']) {
    let finish; const apiName = { start: 'openLive', refresh: 'getLiveStatus', advance: 'advanceLive', clear: 'clearLive' }[method]; const f = fixture({ [apiName]: () => new Promise((resolve) => { finish = resolve; }) });
    if (method !== 'start') await f.controller.start('review-1'); const pending = f.controller[method](method === 'advance' ? 'b' : 'review-1'); f.controller.invalidate(); finish(method === 'clear' ? { cleared: true } : snapshot({ revision: 2 })); await pending; assert.equal(f.controller.snapshot, null); assert.equal(f.controller.valid, false);
  }
});
test('duplicate clicks remain gated until the first request settles', async () => {
  let finish; let count = 0; const f = fixture({ advanceLive: () => { count++; return new Promise((resolve) => { finish = resolve; }); } }); await f.controller.start('review-1'); const pending = f.controller.advance('b'); assert.equal(f.controller.pending, true); await f.controller.advance('c'); await f.controller.clear(); await f.controller.refresh(); assert.equal(count, 1); finish(snapshot({ revision: 2, current: track('b') })); await pending; assert.equal(f.controller.pending, false);
});
test('failed open never falls back, and a failed active request freezes ranked actions with safe guidance', async () => {
  const f = fixture({ openLive: async () => { throw new Error("Error invoking remote method: [live_not_ready] /Users/private/music"); } }); await f.controller.start('review-1'); assert.equal(f.controller.snapshot, null); assert.equal(f.controller.valid, false); assert.doesNotMatch(f.controller.error, /Users|remote method|live_not_ready/);
  const g = fixture({ advanceLive: async () => { throw new Error('[stale_live] /secret'); } }); await g.controller.start('review-1'); await g.controller.advance('b'); assert.equal(g.controller.snapshot.current.id, 'a'); assert.equal(g.controller.valid, false); const count = g.calls.length; await g.controller.advance('c'); assert.equal(g.calls.length, count); assert.doesNotMatch(g.controller.error, /secret|stale_live/);
});
test('mismatched session/review or non-advancing revision cannot replace the displayed snapshot', async () => {
  for (const patch of [{ sessionId: 'other' }, { sourceReviewId: 'other' }, { revision: 1 }, { revision: 0 }]) { const f = fixture({ advanceLive: async () => snapshot(patch) }); await f.controller.start('review-1'); await f.controller.advance('b'); assert.equal(f.controller.snapshot.current.id, 'a'); assert.equal(f.controller.valid, false); }
  const g = fixture({ openLive: async () => snapshot({ sourceReviewId: 'other' }) }); await g.controller.start('review-1'); assert.equal(g.controller.snapshot, null);
});
test('disconnect invalidation can preserve explanatory state while rejecting pending results', async () => {
  let finish; const f = fixture({ getLiveStatus: () => new Promise((resolve) => { finish = resolve; }) }); await f.controller.start('review-1'); const refreshing = f.controller.refresh(); f.controller.invalidate({ preserveSnapshot: true }); f.block(); finish(snapshot({ revision: 2, current: track('b') })); await refreshing; assert.equal(f.controller.snapshot.current.id, 'a'); assert.equal(f.controller.valid, false); await f.controller.advance('b'); assert.equal(f.calls.length, 1);
});
test('complete session has no next action, while authoritative refresh can recover a failed request', async () => {
  const f = fixture({ openLive: async () => snapshot({ state: 'complete', candidates: [] }) }); await f.controller.start('review-1'); await f.controller.advance('b'); assert.equal(f.calls.length, 0);
  let fail = true; const g = fixture({ getLiveStatus: async () => { if (fail) throw new Error('offline'); return snapshot({ revision: 2 }); } }); await g.controller.start('review-1'); await g.controller.refresh(); assert.equal(g.controller.valid, false); fail = false; await g.controller.refresh(); assert.equal(g.controller.valid, true); assert.equal(g.controller.snapshot.revision, 2);
});
test('elapsed display advances monotonically from authoritative seconds, pauses offline, and resets on manual advance', () => {
  const clock = new LiveElapsedClock(); const first = snapshot(); assert.equal(clock.read(first, true, 1000), 12); assert.equal(clock.read(first, true, 3500), 14.5); assert.equal(clock.read(first, false, 4000), 15); assert.equal(clock.read(first, false, 20000), 15); assert.equal(clock.read(first, true, 21000), 15); assert.equal(clock.read(first, true, 22000), 16);
  const next = snapshot({ revision: 2, elapsedSeconds: 0 }); assert.equal(clock.read(next, true, 23000), 0); assert.equal(clock.read(next, true, 24500), 1.5); assert.equal(clock.read(null, false, 25000), 0);
});
