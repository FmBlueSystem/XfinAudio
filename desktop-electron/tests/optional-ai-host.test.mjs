import test from 'node:test';import assert from 'node:assert/strict';import {createRequire} from 'node:module';import {mkdtemp,realpath,mkdir,writeFile,rm,symlink} from 'node:fs/promises';import os from 'node:os';import path from 'node:path';import {fileURLToPath} from 'node:url';
const require=createRequire(import.meta.url),{OptionalAiHost}=require('../.out/main/optional-ai-host.js'),{validateRequest}=require('../.out/main/security.js'),{PythonBridge}=require('../.out/main/bridge.js');
const id='11111111-1111-4111-8111-111111111111',rev='a'.repeat(64),recipient='https://api.nan.builders/v1/chat/completions',deferred=()=>{let resolve;return {promise:new Promise(r=>resolve=r),resolve:v=>resolve(v)}},python=process.env.XFIN_PYTHON,coreRoot=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
function fixture(){const calls=[];let choose=async()=>null,confirm=async()=>true,closing=false,endpoint=recipient,auto=false,firstTurn=true,prepared='editor';const host=new OptionalAiHost({request:async(method,params)=>{calls.push([method,params]);if(method==='ai.prepare'){prepared=String(params.surface);return {previewId:id,surface:prepared,firstTurn,recipient:endpoint,disclosure:['Solicitud sin pistas'],requestPreview:'Acorta a 2 temas'};}if(method==='ai.confirmation')return {previewId:id,surface:prepared,recipient:endpoint,disclosure:['Solicitud sin pistas'],requestPreview:'Acorta a 2 temas'};if(method==='ai.run')return {cancelled:false,result:{resultId:id}};return {revision:rev};},choose:()=>choose(),confirm:summary=>{calls.push(['dialog',summary]);return confirm();},cancel:async()=>{calls.push(['cancel']);return {cancelled:true};},autoAuthorize:async()=>auto,isClosing:()=>closing});return {host,calls,setChoose:v=>choose=v,setConfirm:v=>confirm=v,setAuto:v=>auto=v,setFirstTurn:v=>firstTurn=v,close:()=>closing=true,badEndpoint:()=>endpoint='https://elsewhere.example'};}
test('prepare and declined native AI confirmation cannot send a provider request',async()=>{const f=fixture();await f.host.prepare({surface:'editor',request:'Acorta',context:{editId:id}});f.setConfirm(async()=>false);assert.deepEqual(await f.host.ask(id),{cancelled:true,result:null});assert.ok(!f.calls.some(([m])=>m==='ai.run'));});
test('only an owned preview and fixed disclosed recipient can receive confirmed authority',async()=>{const f=fixture();await assert.rejects(f.host.ask(id));await f.host.prepare({surface:'editor',request:'Acorta',context:{editId:id}});await f.host.ask(id);assert.deepEqual(f.calls.find(([m])=>m==='ai.run'),['ai.run',{previewId:id,confirmed:true}]);const g=fixture();await g.host.prepare({surface:'editor',request:'Acorta',context:{editId:id}});g.badEndpoint();await assert.rejects(g.host.ask(id));assert.ok(!g.calls.some(([m])=>m==='ai.run'));});
test('cancel or close while confirmation waits cannot turn a later yes into a request',async()=>{for(const close of [false,true]){const f=fixture(),wait=deferred();f.setConfirm(()=>wait.promise);await f.host.prepare({surface:'editor',request:'Acorta',context:{editId:id}});const asking=f.host.ask(id);await new Promise(r=>setImmediate(r));if(close)f.close();else assert.deepEqual(await f.host.cancel(),{cancelled:true});wait.resolve(true);if(close)await assert.rejects(asking);else assert.deepEqual(await asking,{cancelled:true,result:null});assert.ok(!f.calls.some(([m])=>m==='ai.run'));}});
test('native credential chooser forwards only canonical regular file metadata; cancel preserves state',async()=>{const root=await realpath(await mkdtemp(path.join(os.tmpdir(),'xfin-ai-picker-'))),filename=path.join(root,'dummy.env');await writeFile(filename,'DUMMY-NOT-A-CREDENTIAL');const f=fixture();try{await f.host.choose({revision:rev});assert.ok(!f.calls.some(([m])=>m==='ai.credential.set'));f.setChoose(async()=>filename);await f.host.choose({revision:rev});assert.deepEqual(f.calls.find(([m])=>m==='ai.credential.set'),['ai.credential.set',{revision:rev,path:filename}]);const link=path.join(root,'link.env');await symlink(filename,link);f.setChoose(async()=>link);await assert.rejects(f.host.choose({revision:rev}));}finally{await rm(root,{recursive:true,force:true});}});
test('AI public IPC cannot carry key/path/endpoint/transport/confirmation or invented context',()=>{assert.deepEqual(validateRequest('getAiStatus'),{});assert.deepEqual(validateRequest('prepareAiRequest',{surface:'editor',request:'Acorta',context:{editId:id}}),{surface:'editor',request:'Acorta',context:{editId:id}});for(const method of ['chooseAiCredential','clearAiCredential']){assert.deepEqual(validateRequest(method,{revision:rev}),{revision:rev});assert.throws(()=>validateRequest(method,{revision:rev,path:'/private'}));}for(const input of [{surface:'editor',request:'Acorta',context:{editId:id,path:'/private'}},{surface:'editor',request:'x'.repeat(2001),context:{editId:id}},{surface:'unknown',request:'x',context:{}},{surface:'live',request:'',context:{sessionId:id,revision:-1}},{surface:'saved',request:'find',context:{playlistIds:['bad']}},{surface:'connection',request:'send music',context:{}},{surface:'library',request:'x',context:{},key:'secret'}])assert.throws(()=>validateRequest('prepareAiRequest',input));assert.throws(()=>validateRequest('runAiRequest',{previewId:id,confirmed:true}));assert.throws(()=>validateRequest('ai.credential.set',{revision:rev,path:'/private'}));});

test('native credential filesystem failures cannot expose selected paths in IPC diagnostics',async()=>{
 const root=await realpath(await mkdtemp(path.join(os.tmpdir(),'xfin-ai-private-picker-'))),filename=path.join(root,'private-dummy-selected.env');
 try{for(const kind of ['missing','deleted','picker-error']){const f=fixture();if(kind==='deleted'){await writeFile(filename,'DUMMY-ONLY');await rm(filename);}f.setChoose(async()=>{if(kind==='picker-error')throw new Error(`Native file chooser failed for ${filename}`);return filename;});await assert.rejects(f.host.choose({revision:rev}),error=>{assert.equal(error.code,'ai_credentials_unavailable');assert.equal(String(error).includes(root),false);assert.equal(String(error).includes(filename),false);assert.equal(error.cause,undefined);return true;});assert.ok(!f.calls.some(([method])=>method==='ai.credential.set'));assert.equal(f.host.busy,false);}}
 finally{await rm(root,{recursive:true,force:true});}
});

test('renderer cannot supply or expand optional AI timeouts',()=>{for(const surface of ['library','prep','review','connection']){const context=surface==='review'?{reviewId:id}:{};const request=surface==='review'?'':surface==='connection'?'Reply with OK. XfinAudio connection test.':'Fixture request';assert.throws(()=>validateRequest('prepareAiRequest',{surface,request,context,timeout:120}));assert.throws(()=>validateRequest('prepareAiRequest',{surface,request,context:{...context,timeout:120}}));}assert.throws(()=>validateRequest('runAiRequest',{previewId:id,timeout:120}));});
test('editor AI context accepts only the bounded improvement selector or the legacy edit identity',()=>{
 const draftIds=['a'.repeat(64),'b'.repeat(64)],request='Acorta la lista';
 const selector={editId:id,draftIds,includeReplacements:true};
 assert.deepEqual(validateRequest('prepareAiRequest',{surface:'editor',request,context:selector}),{surface:'editor',request,context:selector});
 assert.deepEqual(validateRequest('prepareAiRequest',{surface:'editor',request,context:{editId:id}}),{surface:'editor',request,context:{editId:id}});
 assert.equal(validateRequest('prepareAiRequest',{surface:'editor',request,context:{editId:id,draftIds,includeReplacements:false}}).context.includeReplacements,false);
 const edge=Array.from({length:80},(_,index)=>index.toString(16).padStart(64,'a'));
 assert.deepEqual(validateRequest('prepareAiRequest',{surface:'editor',request,context:{editId:id,draftIds:edge,includeReplacements:true}}).context.draftIds,edge);
 const rejected=[
  {editId:id,draftIds,includeReplacements:'true'},
  {editId:id,draftIds,includeReplacements:1},
  {editId:id,draftIds:[draftIds[0]],includeReplacements:false},
  {editId:id,draftIds:[draftIds[0],draftIds[0]],includeReplacements:false},
  {editId:id,draftIds:[draftIds[0],'/etc/passwd'],includeReplacements:false},
  {editId:id,draftIds:Array.from({length:81},(_,index)=>index.toString(16).padStart(64,'a')),includeReplacements:false},
  {editId:id,draftIds,includeReplacements:false,path:'/private'},
  {editId:id,draftIds},
  {editId:id,includeReplacements:false},
 ];
 for(const context of rejected)assert.throws(()=>validateRequest('prepareAiRequest',{surface:'editor',request,context}));
});

test('persisted automatic authorization sends directly without native confirmation',async()=>{
  const f=fixture();await f.host.prepare({surface:'library',request:'House',context:{}});f.setAuto(true);
  const out=await f.host.ask(id);
  assert.deepEqual(out,{cancelled:false,result:{resultId:id}});
  assert.ok(!f.calls.some(([method])=>method==='ai.confirmation'||method==='dialog'),'skip per-query confirmation');
  assert.deepEqual(f.calls.filter(([method])=>method==='ai.run')[0],['ai.run',{previewId:id,confirmed:true}]);
});

// --- S6: the chat surface, its conversation actions and its per-conversation consent ---
test('chat accepts exactly the review selector and a message of 1 to 2000 characters',()=>{
 const request='¿Qué transiciones son las más débiles?',selector={reviewId:id};
 assert.deepEqual(validateRequest('prepareAiRequest',{surface:'chat',request,context:selector}),{surface:'chat',request,context:selector});
 assert.equal(validateRequest('prepareAiRequest',{surface:'chat',request:'x'.repeat(2000),context:selector}).request.length,2000);
 for(const rejected of [
  {surface:'chat',request:'',context:selector},
  {surface:'chat',request:'   ',context:selector},
  {surface:'chat',request:'x'.repeat(2001),context:selector},
  {surface:'chat',request:'hola\x00',context:selector},
  {surface:'chat',request:42,context:selector},
  {surface:'chat',request,context:{}},
  {surface:'chat',request,context:{playlistId:'1'}},
  {surface:'chat',request,context:{reviewId:'../private'}},
  {surface:'chat',request,context:{reviewId:id,path:'/private'}},
  {surface:'chat',request,context:{reviewId:id,timeout:120}},
 ])assert.throws(()=>validateRequest('prepareAiRequest',rejected));
 // The renderer still cannot confirm its own send, whatever the surface.
 assert.throws(()=>validateRequest('runAiRequest',{previewId:id,confirmed:true}));
});
test('conversation history and reset cross the bridge as parameterless actions',()=>{
 for(const method of ['aiChatHistory','aiChatReset']){
  assert.deepEqual(validateRequest(method),{});
  assert.deepEqual(validateRequest(method,{}),{});
  for(const rejected of [{reviewId:id},{conversation:[]},{previewId:id},[],null,'x'])assert.throws(()=>validateRequest(method,rejected));
 }
});
test('the native dialog is shown on the first chat turn and skipped on later turns of that conversation',async()=>{
 const f=fixture();
 await f.host.prepare({surface:'chat',request:'¿Qué transiciones son las más débiles?',context:{reviewId:id}});
 assert.deepEqual(await f.host.ask(id),{cancelled:false,result:{resultId:id}});
 assert.equal(f.calls.filter(([method])=>method==='dialog').length,1,'the first turn is authorised in the native dialog');
 assert.deepEqual(f.calls.find(([method])=>method==='ai.run'),['ai.run',{previewId:id,confirmed:true}]);
 f.setFirstTurn(false);
 const second=await f.host.prepare({surface:'chat',request:'¿Qué pista quitarías y por qué?',context:{reviewId:id}});
 assert.equal(second.firstTurn,false);
 assert.deepEqual(await f.host.ask(id),{cancelled:false,result:{resultId:id}});
 assert.equal(f.calls.filter(([method])=>method==='dialog').length,1,'a later turn of the same conversation reuses the first consent');
 assert.equal(f.calls.filter(([method])=>method==='ai.run').length,2);
 assert.deepEqual(f.calls.filter(([method])=>method==='ai.run').at(-1),['ai.run',{previewId:id,confirmed:true}]);
});
test('only an explicit continuing chat preview skips the dialog',async()=>{
 for(const firstTurn of [true,undefined,'false',0]){
  const f=fixture();f.setFirstTurn(firstTurn);
  await f.host.prepare({surface:'chat',request:'Hola',context:{reviewId:id}});
  await f.host.ask(id);
  assert.equal(f.calls.filter(([method])=>method==='dialog').length,1,`firstTurn ${String(firstTurn)} must still ask`);
 }
 const review=fixture();
 await review.host.prepare({surface:'review',request:'',context:{reviewId:id}});
 await review.host.ask(id);
 assert.equal(review.calls.filter(([method])=>method==='dialog').length,1,'the review commentary keeps its per-request dialog');
});
test('declining the first chat turn sends nothing at all',async()=>{
 const f=fixture();f.setConfirm(async()=>false);
 await f.host.prepare({surface:'chat',request:'Hola',context:{reviewId:id}});
 assert.deepEqual(await f.host.ask(id),{cancelled:true,result:null});
 assert.ok(!f.calls.some(([method])=>method==='ai.run'));
});
test('automatic authorization keeps its meaning for chat, first turn included',async()=>{
 const f=fixture();f.setAuto(true);
 await f.host.prepare({surface:'chat',request:'Hola',context:{reviewId:id}});
 assert.deepEqual(await f.host.ask(id),{cancelled:false,result:{resultId:id}});
 assert.ok(!f.calls.some(([method])=>method==='ai.confirmation'||method==='dialog'),'the persisted setting still replaces the dialog');
 assert.deepEqual(f.calls.find(([method])=>method==='ai.run'),['ai.run',{previewId:id,confirmed:true}]);
});

// Cross-boundary: the Electron host against the real Python core. It cannot pass until the
// core implements the chat surface, `firstTurn`, `ai.chat.history` and `ai.chat.reset`.
const chatScript=`import io,json,sys,urllib.request
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
    return io.BytesIO(json.dumps({'choices':[{'message':{'content':'Quita la tercera pista: su energia rompe la curva.'}}]}).encode())
backend.optional_ai.transport=fake
JsonlServer(backend,sys.stdout).run(sys.stdin.buffer)
`;
test('the chat surface and its conversation actions agree with the Python core',{skip:!python,timeout:30000},async()=>{
 const data=await realpath(await mkdtemp('/tmp/xfin-chat-host-')),credential=path.join(data,'selected.env');
 await writeFile(credential,'NAN_API_KEY=dummy-test-only\n',{mode:0o600});
 const core=new PythonBridge(python,['-c',chatScript,data],{...process.env,PYTHONPATH:path.join(coreRoot,'src'),PYTHONDONTWRITEBYTECODE:'1',XFINAUDIO_AI_ENABLED:'1',NAN_API_BASE:'https://unapproved.invalid',NAN_API_KEY:'inherited-dummy-must-not-be-used'});
 const dialogs=[];
 const host=new OptionalAiHost({request:(method,params)=>core.request(method,params??{}),choose:async()=>null,confirm:async summary=>{dialogs.push(summary);return true;},cancel:()=>Promise.resolve({cancelled:false}),autoAuthorize:async()=>false,isClosing:()=>false});
 try{
  const initial=await core.request('ai.status');
  assert.deepEqual(await core.request('ai.chat.history'),{conversation:[]},'a fresh core keeps an empty conversation');
  await core.request('library.scan',{root:path.join(coreRoot,'desktop-electron/tests/fixtures/music')});
  const review=await core.request('prep.generate',{targetTrackCount:4,name:'Chat host fixture'});
  const enabled=await core.request('ai.settings.update',{revision:initial.revision,enabled:true});
  await core.request('ai.credential.set',{revision:enabled.revision,path:credential});
  const first=await host.prepare({surface:'chat',request:'¿Qué transiciones son las más débiles?',context:{reviewId:review.reviewId}});
  assert.equal(first.surface,'chat');
  assert.equal(first.firstTurn,true,'a fresh conversation reports its first turn');
  const turn=await host.ask(first.previewId);
  assert.equal(turn.cancelled,false);
  assert.equal(turn.result.kind,'chat');
  assert.equal(turn.result.proposal,null);
  assert.equal(turn.result.canApply,false);
  assert.equal(turn.result.listChanged,false);
  assert.ok(turn.result.text.length>=1&&turn.result.text.length<=4000,'the reply is 1 to 4000 characters');
  assert.deepEqual(turn.result.conversation.map(message=>message.role),['user','assistant']);
  assert.equal(turn.result.conversation[0].text,'¿Qué transiciones son las más débiles?');
  assert.equal(dialogs.length,1,'the first turn of a conversation is consented in the native dialog');
  const second=await host.prepare({surface:'chat',request:'¿Qué pista quitarías y por qué?',context:{reviewId:review.reviewId}});
  assert.equal(second.firstTurn,false,'the stored conversation is no longer empty');
  const next=await host.ask(second.previewId);
  assert.equal(next.result.kind,'chat');
  assert.equal(next.result.listChanged,false);
  assert.equal(dialogs.length,1,'a later turn of the same conversation reuses the first consent');
  assert.deepEqual((await core.request('ai.chat.history')).conversation.map(message=>message.role),['user','assistant','user','assistant']);
  assert.deepEqual(await core.request('ai.chat.reset'),{conversation:[]});
  assert.equal((await host.prepare({surface:'chat',request:'Otra vez',context:{reviewId:review.reviewId}})).firstTurn,true,'reset starts a new conversation');
 }finally{await core.close();await rm(data,{recursive:true,force:true});}
});
