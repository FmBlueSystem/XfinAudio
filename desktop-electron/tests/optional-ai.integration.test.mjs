import test from 'node:test';import assert from 'node:assert/strict';import {mkdtemp,realpath,rm,writeFile,readFile} from 'node:fs/promises';import {createRequire} from 'node:module';import path from 'node:path';import {fileURLToPath} from 'node:url';
const require=createRequire(import.meta.url),{PythonBridge}=require('../.out/main/bridge.js'),root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..'),python=process.env.XFIN_PYTHON;
const script=`import io,json,sys,urllib.request
from pathlib import Path
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.server import JsonlServer
from xfinaudio.ai import nan_client

def forbidden(*args,**kwargs): raise AssertionError('REAL NETWORK FORBIDDEN IN OFFLINE TEST')
nan_client._urlopen=forbidden
urllib.request.urlopen=forbidden
urllib.request.build_opener=forbidden
root=Path(sys.argv[1])
backend=HeadlessBackend(root)
def fake(request,*,timeout):
    assert request.full_url==nan_client.DEFAULT_ENDPOINT
    assert request.get_header('Authorization')=='Bearer dummy-test-only'
    body=request.data.decode()
    assert str(root) not in body and 'Electron test' not in body
    with (root/'fake-requests.jsonl').open('a') as log: log.write(json.dumps({'recipient':request.full_url,'body':body})+'\\n')
    return io.BytesIO(json.dumps({'choices':[{'message':{'content':'{"operation":"shorten_tracks","target":2}'}}]}).encode())
backend.optional_ai.transport=fake
JsonlServer(backend,sys.stdout).run(sys.stdin.buffer)
`;
test('real Qt-free AI bridge uses only injected transport and explicit local editor review/save',{skip:!python,timeout:20000},async()=>{
 const data=await realpath(await mkdtemp('/tmp/xfin-ai-offline-')),credential=path.join(data,'selected.env'),log=path.join(data,'fake-requests.jsonl');await writeFile(credential,'NAN_API_KEY=dummy-test-only\n');
 const start=()=>new PythonBridge(python,['-c',script,data],{...process.env,PYTHONPATH:path.join(root,'src'),NAN_API_KEY:'inherited-dummy-must-not-be-used',XFINAUDIO_AI_ENABLED:'1',NAN_API_BASE:'https://unapproved.invalid'});let core=start();
 try{
  const initial=await core.request('ai.status');assert.equal(initial.enabled,false);assert.equal(initial.configured,false);
  await core.request('library.scan',{root:path.join(root,'desktop-electron/tests/fixtures/music')});const review=await core.request('prep.generate',{targetTrackCount:4,name:'Offline AI fixture'});const saved=await core.request('playlist.save',{name:'Original unchanged until Save',reviewId:review.reviewId});const edit=await core.request('playlist.edit.open',{playlistId:saved.id});
  const enabled=await core.request('ai.settings.update',{revision:initial.revision,enabled:true});const configured=await core.request('ai.credential.set',{revision:enabled.revision,path:credential});assert.equal(configured.credentialLabel,'selected.env');assert.equal(JSON.stringify(configured).includes('dummy-test-only'),false);assert.equal(JSON.stringify(configured).includes(data),false);
  const preview=await core.request('ai.prepare',{surface:'editor',request:'Acorta a 2 temas',context:{editId:edit.editId}});await assert.rejects(readFile(log),error=>error.code==='ENOENT');await assert.rejects(core.request('ai.run',{previewId:preview.previewId,confirmed:false}));await assert.rejects(readFile(log),error=>error.code==='ENOENT');
  // F6: the exact retained body is inspectable before consenting, and inspecting it is not a send.
  const inspected=await core.request('ai.payload',{previewId:preview.previewId});
  assert.equal(inspected.previewId,preview.previewId);assert.equal(inspected.surface,'editor');assert.equal(inspected.recipient,preview.recipient);assert.equal(inspected.truncated,false);assert.equal(inspected.bytes,Buffer.byteLength(inspected.body));assert.equal(inspected.request,'Acorta a 2 temas');
  assert.equal(inspected.body.includes('shorten to 2 tracks'),false);assert.equal(JSON.parse(inspected.body).messages.length,2);
  await assert.rejects(readFile(log),error=>error.code==='ENOENT');
  const answer=await core.request('ai.run',{previewId:preview.previewId,confirmed:true});assert.equal(answer.result.kind,'editor_request');
  // The inspected body is byte-identical to the body the provider transport actually received.
  assert.equal(JSON.parse((await readFile(log,'utf8')).trim().split('\n')[0]).body,inspected.body);
  await assert.rejects(core.request('ai.payload',{previewId:preview.previewId}),error=>error.code==='stale_ai');const applied=await core.request('ai.apply',{resultId:answer.result.resultId});assert.equal(applied.data.request,'shorten to 2 tracks');assert.equal((await core.request('playlist.open',{playlistId:saved.id})).tracks.length,4);
  const local=await core.request('playlist.edit.preview',{editId:edit.editId,trackIds:edit.tracks.map(t=>t.id),request:applied.data.request});assert.equal(local.tracks.length,2);assert.equal((await core.request('playlist.open',{playlistId:saved.id})).tracks.length,4);await core.request('playlist.edit.save',{editId:edit.editId,name:'Explicitly saved local edit',trackIds:local.tracks.map(t=>t.id)});
  assert.equal((await readFile(log,'utf8')).trim().split('\n').length,1);assert.equal((await readFile(path.join(data,'settings.json'),'utf8')).includes('dummy-test-only'),false);
  await core.close();core=start();const restored=await core.request('ai.status');assert.equal(restored.enabled,true);assert.equal(restored.configured,true);assert.equal((await core.request('playlist.open',{playlistId:saved.id})).tracks.length,2);await assert.rejects(core.request('ai.apply',{resultId:answer.result.resultId}),error=>error.code==='stale_ai');
 }finally{await core.close();await rm(data,{recursive:true,force:true});}
});
