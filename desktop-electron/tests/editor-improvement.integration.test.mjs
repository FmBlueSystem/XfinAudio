import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp, readFile, realpath, rm, stat, writeFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const require = createRequire(import.meta.url);
const {PythonBridge} = require('../.out/main/bridge.js');
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const music = path.join(root, 'desktop-electron/tests/fixtures/music');
const python = process.env.XFIN_PYTHON;

// The real Python core runs here, but every provider call is answered by a locally
// injected transport that may only return tokens it read from the request payload.
const script = `import io,json,sys
from pathlib import Path
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.server import JsonlServer
from xfinaudio.ai import nan_client
import urllib.request

def forbidden(*args,**kwargs): raise AssertionError('REAL NETWORK FORBIDDEN IN OFFLINE TEST')
nan_client._urlopen=forbidden
urllib.request.urlopen=forbidden
urllib.request.build_opener=forbidden
data=Path(sys.argv[1])
music=sys.argv[2]
backend=HeadlessBackend(data)
def fake(request,*,timeout):
    assert request.full_url==nan_client.DEFAULT_ENDPOINT
    body=request.data.decode('utf-8')
    assert music not in body
    with (data/'fake-requests.jsonl').open('a') as log: log.write(body+'\\n')
    payload=json.loads(json.loads(body)['messages'][-1]['content'])
    tokens=[item['token'] for item in payload['context']['candidates']]
    content=json.dumps({'orderedTrackIds':list(reversed(tokens)),'rationale':'Orden invertido localmente.'})
    return io.BytesIO(json.dumps({'choices':[{'message':{'content':content}}]}).encode())
backend.optional_ai.transport=fake
JsonlServer(backend,sys.stdout).run(sys.stdin.buffer)
`;

test('real Qt-free core binds an AI improvement to the open draft and only playlist.edit.save_improvement persists the validated order', {skip: !python, timeout: 60000}, async () => {
  const data = await realpath(await mkdtemp('/tmp/xfin-improve-'));
  const credential = path.join(data, 'selected.env');
  const requests = path.join(data, 'fake-requests.jsonl');
  await writeFile(credential, 'NAN_API_KEY=dummy-test-only\n');
  const start = () => new PythonBridge(python, ['-c', script, data, music], {...process.env, PYTHONPATH: path.join(root, 'src'), NAN_API_KEY: 'inherited-dummy-must-not-be-used', XFINAUDIO_AI_ENABLED: '1', NAN_API_BASE: 'https://unapproved.invalid'});
  let core = start();
  try {
    const scan = await core.request('library.scan', {root: music});
    assert.ok(scan.tracks.length >= 2);
    const review = await core.request('prep.generate', {targetTrackCount: 4, name: 'Improvement fixture'});
    const saved = await core.request('playlist.save', {name: 'Original order', reviewId: review.reviewId});
    const edit = await core.request('playlist.edit.open', {playlistId: saved.id});
    const draftIds = edit.tracks.map(track => track.id);
    assert.equal(draftIds.length, 4);

    const status = await core.request('ai.status');
    assert.equal(status.enabled, false);
    const enabled = await core.request('ai.settings.update', {revision: status.revision, enabled: true});
    const configured = await core.request('ai.credential.set', {revision: enabled.revision, path: credential});
    assert.equal(configured.credentialLabel, 'selected.env');

    // The improvement selector is the only context that authorizes a bounded candidate set.
    const preview = await core.request('ai.prepare', {surface: 'editor', request: 'Reordena sin perder pistas', context: {editId: edit.editId, draftIds, includeReplacements: false}});
    const answer = await core.request('ai.run', {previewId: preview.previewId, confirmed: true});
    assert.equal(answer.result.kind, 'improvement');
    const applied = await core.request('ai.apply', {resultId: answer.result.resultId});
    assert.equal(applied.surface, 'editor');
    const proposal = applied.data;
    assert.match(proposal.proposalId, /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/);
    assert.match(proposal.digest, /^[a-f0-9]{64}$/);
    assert.deepEqual(proposal.before.map(track => track.id), draftIds);
    const improved = proposal.after.map(track => track.id);
    assert.deepEqual(improved, [...draftIds].reverse());
    assert.notDeepEqual(improved, draftIds);
    assert.deepEqual(proposal.addedIds, []);
    assert.deepEqual(proposal.removedIds, []);

    // Applying a proposal previews it in memory; the playlist on disk is still the original order.
    assert.deepEqual((await core.request('playlist.open', {playlistId: saved.id})).tracks.map(track => track.id), draftIds);
    const sent = await readFile(requests, 'utf8');
    assert.equal(sent.includes(music), false);
    assert.equal(draftIds.some(id => sent.includes(id)), false);

    // The real core rejects a mismatched digest, a mismatched proposal id, and a mutated draft order.
    const save = extra => core.request('playlist.edit.save_improvement', {editId: edit.editId, name: extra.name, proposalId: extra.proposalId, digest: extra.digest, draftIds: extra.draftIds});
    await assert.rejects(save({name: 'Rejected', proposalId: proposal.proposalId, digest: 'f'.repeat(64), draftIds: improved}), error => error.code === 'invalid_edit');
    await assert.rejects(save({name: 'Rejected', proposalId: '00000000-0000-0000-0000-000000000000', digest: proposal.digest, draftIds: improved}), error => error.code === 'invalid_edit');
    await assert.rejects(save({name: 'Rejected', proposalId: proposal.proposalId, digest: proposal.digest, draftIds: [...improved].reverse()}), error => error.code === 'stale_edit');
    const untouched = await core.request('playlist.open', {playlistId: saved.id});
    assert.equal(untouched.name, 'Original order');
    assert.deepEqual(untouched.tracks.map(track => track.id), draftIds);

    // The renderer's exact save payload persists the improvement order the core validated.
    const snapshot = await core.request('playlist.edit.save_improvement', {editId: edit.editId, name: 'Improved order', proposalId: proposal.proposalId, digest: proposal.digest, draftIds: improved});
    assert.equal(snapshot.name, 'Improved order');
    assert.deepEqual(snapshot.tracks.map(track => track.id), improved);
    assert.notEqual(snapshot.editId, edit.editId);

    // The order is on disk, and a restarted core reads it back from the same data directory.
    assert.ok((await stat(path.join(data, 'playlists.db'))).size > 0);
    await core.close();
    core = start();
    const reopened = await core.request('playlist.open', {playlistId: saved.id});
    assert.equal(reopened.name, 'Improved order');
    assert.deepEqual(reopened.tracks.map(track => track.id), improved);
  } finally {
    await core.close();
    await rm(data, {recursive: true, force: true});
  }
});
