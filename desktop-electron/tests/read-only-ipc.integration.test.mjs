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
// The core runs one job worker. `JsonlServer.process_line` answers only `track.resolve`
// and `prep.catalog` inline while a job is active and refuses every other method with
// `busy`, so no Electron-only read whitelist can be wider than those two.
const script = `import sys,time
from pathlib import Path
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.server import JsonlServer

backend = HeadlessBackend(Path(sys.argv[1]))
original = backend.execute

def delayed(method, params, *, cancellation_token=None, progress=None):
    if method == 'library.scan':
        time.sleep(2.5)
    return original(method, params, cancellation_token=cancellation_token, progress=progress)

backend.execute = delayed
JsonlServer(backend, sys.stdout).run(sys.stdin.buffer)
`;
test('while a core job is active only the inline reads answer and every other read stays busy', {skip: !python, timeout: 30000}, async () => {
  const data = await realpath(await mkdtemp('/tmp/xfin-reads-'));
  const core = new PythonBridge(python, ['-c', script, data], {...process.env, PYTHONPATH: path.join(root, 'src')});
  try {
    const scan = core.request('library.scan', {root: music});
    // The reader thread registers the job before it reads the next request, so these
    // reads are guaranteed to arrive while the single worker is occupied.
    const catalog = await core.request('prep.catalog');
    assert.equal(catalog.strategies.length, 11);
    for (const method of ['library.list', 'settings.get', 'metadata.report', 'playlist.list']) {
      await assert.rejects(core.request(method), (error) => error.code === 'busy', `${method} must stay refused while the worker is busy`);
    }
    const scanned = await scan;
    assert.equal(scanned.tracks.length, 8);
    // The same reads answer once the worker is free, so the refusal above is exclusivity, not breakage.
    assert.equal((await core.request('library.list')).tracks.length, 8);
    assert.equal((await core.request('settings.get')).previewVolume, 0.7);
  } finally {
    await core.close();
    await rm(data, {recursive: true, force: true});
  }
});
