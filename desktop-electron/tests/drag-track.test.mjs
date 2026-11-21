import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const {createDragTracks} = require('../.out/main/drag-track.js');

const ID = 'a'.repeat(64), OTHER = 'b'.repeat(64), UNKNOWN = 'c'.repeat(64);

/** The exact liveFollow answer shape the core sends: only public ids, never a path. */
const answer = (...ids) => ({
  available: true, reason: null, sessionStartedAt: '2026-10-01T22:00:00Z',
  playing: [], current: null, playedCount: 0,
  suggestions: ids.map((id) => ({id, title: `Título ${id}`, artist: 'Artista', bpm: 124, key: '8A', energy: 5, duration: 200, score: 0.8})),
});

/**
 * The four dependencies as the host passes them, recorded instead of run:
 * no Electron, no filesystem, no core. `resolved` is what track.resolve answers.
 */
function harness({resolved = {}, existing = []} = {}) {
  const calls = [], drags = [];
  const files = new Set(existing);
  const request = async (method, params) => {
    calls.push({method, params});
    const file = resolved[params.trackId];
    if (!file) throw new Error('Track is missing or outside the authorized library');
    return {path: file, mime: 'audio/aiff', identity: {}};
  };
  const startDrag = (drag) => drags.push(drag);
  const fileExists = async (file) => files.has(file);
  const icon = {kind: 'icon'};
  const tracks = createDragTracks({request, startDrag, fileExists, icon});
  return {tracks, calls, drags, files};
}

test('a cached suggestion id starts one drag with its file and no core round trip', async () => {
  const {tracks, calls, drags} = harness({resolved: {[ID]: '/music/a.aiff'}, existing: ['/music/a.aiff']});

  await tracks.remember(answer(ID));
  assert.deepEqual(calls, [{method: 'track.resolve', params: {trackId: ID}}], 'the answer is resolved ahead of the drag');
  calls.length = 0;

  assert.equal(await tracks.drag({trackId: ID}), null, 'a drag answers the renderer with nothing');
  assert.deepEqual(drags, [{file: '/music/a.aiff', icon: {kind: 'icon'}}], 'exactly one drag starts, with the resolved file');
  assert.deepEqual(calls, [], 'a cached suggestion drags without waiting for the core');
});

test('an id the last answer did not suggest is resolved at drag time', async () => {
  const {tracks, calls, drags} = harness({resolved: {[OTHER]: '/music/b.aiff'}, existing: ['/music/b.aiff']});

  await tracks.remember(answer());
  assert.deepEqual(calls, [], 'an answer without suggestions resolves nothing');

  await tracks.drag({trackId: OTHER});
  assert.deepEqual(calls, [{method: 'track.resolve', params: {trackId: OTHER}}], 'the drag resolves the uncached id once');
  assert.deepEqual(drags, [{file: '/music/b.aiff', icon: {kind: 'icon'}}]);
});

test('an unknown id, a malformed id, extra parameters or a missing file start no drag and throw nothing', async () => {
  const {tracks, calls, drags} = harness({resolved: {[ID]: '/music/gone.aiff'}, existing: []});

  const malformed = [
    undefined, null, 'track', [], [{trackId: ID}], {}, {trackId: ''}, {trackId: ID.slice(1)},
    {trackId: 'A'.repeat(64)}, {trackId: '../music/a.aiff'}, {trackId: 42}, {trackId: {id: ID}},
    {trackId: ID, path: '/music/a.aiff'}, {trackId: ID, file: '/music/a.aiff'}, {trackId: ID, icon: 'x'},
    {path: '/music/a.aiff'}, {name: 'trackId', trackId: ID},
  ];
  for (const params of malformed) {
    await assert.doesNotReject(() => tracks.drag(params), `drag(${JSON.stringify(params)}) must not reject`);
    assert.equal(await tracks.drag(params), null, `drag(${JSON.stringify(params)}) must answer nothing`);
  }
  assert.deepEqual(drags, [], 'nothing malformed reaches startDrag');
  assert.deepEqual(calls, [], 'a malformed or widened request never reaches the core');

  // A well-formed id the core refuses, and a file deleted since the answer, both stay silent.
  await assert.doesNotReject(() => tracks.drag({trackId: UNKNOWN}));
  assert.deepEqual(calls.map((call) => call.params), [{trackId: UNKNOWN}], 'an id the core does not resolve is asked for once');
  await assert.doesNotReject(() => tracks.remember(answer(ID)));
  calls.length = 0;
  await assert.doesNotReject(() => tracks.drag({trackId: ID}));
  assert.deepEqual(drags, [], 'a file that no longer exists starts no drag');
  assert.deepEqual(calls, [], 'the vanished file still comes from the cache, without a core round trip');
});

test('each liveFollow answer replaces the cache', async () => {
  const {tracks, calls, drags} = harness({resolved: {[ID]: '/music/a.aiff', [OTHER]: '/music/b.aiff'}, existing: ['/music/a.aiff', '/music/b.aiff']});

  await tracks.remember(answer(ID));
  await tracks.remember(answer(OTHER));
  assert.deepEqual(calls.map((call) => call.params.trackId), [ID, OTHER], 'only the newest answer is resolved ahead');

  await tracks.drag({trackId: ID});
  assert.deepEqual(calls.map((call) => call.params.trackId), [ID, OTHER, ID], 'the replaced id is resolved again at drag time');

  await tracks.remember(answer());
  calls.length = 0;
  await tracks.drag({trackId: OTHER});
  assert.deepEqual(calls.map((call) => call.params.trackId), [OTHER], 'an answer with no suggestions empties the cache');
  assert.equal(drags.length, 2, 'both cached drags still started');
});

test('an answer that resolves late never overwrites the cache of a newer one', async () => {
  const pending = [];
  const calls = [], drags = [];
  const tracks = createDragTracks({
    request: (method, params) => { calls.push(params.trackId); return new Promise((resolve) => pending.push(() => resolve({path: params.trackId === ID ? '/music/a.aiff' : '/music/b.aiff'}))); },
    startDrag: (drag) => drags.push(drag),
    fileExists: async () => true,
    icon: {kind: 'icon'},
  });

  const slow = tracks.remember(answer(ID));
  const fast = tracks.remember(answer(OTHER));
  pending[1]();
  await fast;
  pending[0]();
  await slow;

  await tracks.drag({trackId: OTHER});
  assert.deepEqual(drags, [{file: '/music/b.aiff', icon: {kind: 'icon'}}], 'the newest answer owns the cache');
  assert.deepEqual(calls, [ID, OTHER], 'a cached drag resolves nothing');
});

test('the path never appears in anything returned to the renderer', async () => {
  const secret = '/Users/someone/Music/secret.aiff';
  const {tracks} = harness({resolved: {[ID]: secret}, existing: [secret]});

  const reply = answer(ID);
  await tracks.remember(reply);
  const dragged = await tracks.drag({trackId: ID});
  const uncached = await tracks.drag({trackId: OTHER});

  for (const value of [dragged, uncached, reply])
    assert.equal(JSON.stringify(value ?? null).includes('secret.aiff'), false, 'no answer may carry the file path');
  assert.equal(JSON.stringify(reply).includes('path'), false, 'resolving ahead must not annotate the answer');
});
