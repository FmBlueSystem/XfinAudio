import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp, realpath, rm} from 'node:fs/promises';
import {createRequire} from 'node:module';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const require = createRequire(import.meta.url);
const {PythonBridge} = require('../.out/main/bridge.js');
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const music = path.join(root, 'desktop-electron/tests/fixtures/music');
const python = process.env.XFIN_PYTHON;
// The core runs one job worker, but `JsonlServer.process_line` answers genuinely
// read-only queries inline. This is the same reviewed set as the Electron whitelist
// and as `INLINE_METHODS` in `src/xfinaudio/headless/server.py`.
const readCases = [
  ['library.list', {}],
  ['library.query', {}],
  ['playlist.list', {}],
  ['playlist.open', {playlistId: 1}],
  ['playlist.search', {request: ''}],
  ['playlist.compare', {playlistIds: [1, 2]}],
  ['playlist.deleted.list', {}],
  ['metadata.report', {}],
  ['settings.get', {}],
  ['prep.settings.get', {}],
  ['prep.catalog', {}],
  ['profiles.status', {}],
  ['profiles.settings.get', {}],
  ['loudness.status', {}],
  ['ai.status', {}],
  ['live.status', {sessionId: '11111111-1111-4111-8111-111111111111'}],
  ['track.resolve', {trackId: 'a'.repeat(64)}],
];
// Mutating or job-controlling commands keep the exact busy refusal while the worker runs.
const refusedCases = [
  ['library.scan', {root: music}],
  ['library.rescan', {}],
  ['prep.generate', {targetTrackCount: 3}],
  ['playlist.save', {name: 'Set', reviewId: '11111111-1111-4111-8111-111111111111'}],
  ['playlist.rename', {playlistId: 1, name: 'Set'}],
  ['settings.update', {revision: 'a'.repeat(64), previewVolume: 0.5, watchLibrary: true}],
  ['profiles.complete', {}],
  ['loudness.run', {previewId: '11111111-1111-4111-8111-111111111111', confirmed: true}],
  ['ai.run', {previewId: '11111111-1111-4111-8111-111111111111', confirmed: true}],
  ['serato.commit', {previewId: '11111111-1111-4111-8111-111111111111', confirmed: true}],
];
const script = `import sys,time
from pathlib import Path
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.server import JsonlServer

backend = HeadlessBackend(Path(sys.argv[1]))
original = backend.execute

def delayed(method, params, *, cancellation_token=None, progress=None):
    if method == 'library.scan':
        time.sleep(4.0)
    return original(method, params, cancellation_token=cancellation_token, progress=progress)

backend.execute = delayed
JsonlServer(backend, sys.stdout).run(sys.stdin.buffer)
`;
const outcome = async (core, method, params) => {
  try {
    return {ok: true, value: await core.request(method, params)};
  } catch (error) {
    return {ok: false, code: error.code};
  }
};
test('while a core job is active the reviewed reads answer inline and every write stays busy', {skip: !python, timeout: 40000}, async () => {
  const data = await realpath(await mkdtemp('/tmp/xfin-reads-'));
  const core = new PythonBridge(python, ['-c', script, data], {...process.env, PYTHONPATH: path.join(root, 'src')});
  try {
    const scan = core.request('library.scan', {root: music});
    // The reader thread registers the job before it reads the next request, so these
    // reads are guaranteed to arrive while the single worker is occupied.
    for (const [method, params] of readCases) {
      const result = await outcome(core, method, params);
      assert.notEqual(result.code, 'busy', `${method} must answer inline while the single worker is busy`);
    }
    for (const [method, params] of refusedCases) {
      await assert.rejects(core.request(method, params), (error) => error.code === 'busy', `${method} must stay refused while the worker is busy`);
    }
    const scanned = await scan;
    assert.equal(scanned.tracks.length, 8);
    // The same reads answer once the worker is free, so the refusals above are exclusivity, not breakage.
    assert.equal((await core.request('library.list')).tracks.length, 8);
    assert.equal((await core.request('settings.get')).previewVolume, 0.7);
    assert.equal((await core.request('metadata.report')).totalTracks, 8);
  } finally {
    await core.close();
    await rm(data, {recursive: true, force: true});
  }
});
