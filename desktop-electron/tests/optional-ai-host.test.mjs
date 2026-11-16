import test from 'node:test';import assert from 'node:assert/strict';import {createRequire} from 'node:module';import {mkdtemp,realpath,mkdir,writeFile,readFile,rm,symlink} from 'node:fs/promises';import os from 'node:os';import path from 'node:path';import {fileURLToPath} from 'node:url';
const require=createRequire(import.meta.url),{OptionalAiHost}=require('../.out/main/optional-ai-host.js'),{validateRequest}=require('../.out/main/security.js'),{PythonBridge}=require('../.out/main/bridge.js'),{ListChatController,listChatActionText}=require('../.out/renderer/list-chat.js');
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
// S4: applying a proposed change carries its opaque action id and nothing the renderer could
// invent (no position, no type, no confirmation flag); the click is the whole consent.
test('applying a proposed change crosses the bridge as exactly one opaque action id',()=>{
 assert.deepEqual(validateRequest('aiChatApply',{actionId:id}),{actionId:id});
 for(const rejected of [undefined,{},{actionId:'../private'},{actionId:'not-a-uuid'},{actionId:'AAAAAAAA-BBBB-4CCC-8DDD-EEEEEEEEEEEE'},{actionId:42},{actionId:id.slice(1)},[],null,'x',{actionId:id,position:1},{actionId:id,to:2},{actionId:id,type:'replace'},{actionId:id,reviewId:id},{actionId:id,confirmed:true},])assert.throws(()=>validateRequest('aiChatApply',rejected));
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

// Cross-boundary: the Electron host against the real Python core, which implements the chat
// surface, `firstTurn`, the proposed changes (`ai.chat.history`, `ai.chat.apply`) and
// `ai.chat.reset` behind the bridge.
const reply='Mueve la pista 1 a la posición 2: la curva de energía sube parejo.',
 reason='La energía sube parejo si la 1 va después de la 2.',
 searchRequest='Busca en la biblioteca y propón cambios.',
 searchReply='Encontré dos pistas que encajan: quito la 3, sumo la 6 al final y cambio la 1 por la 5.',
 removeReason='Sobra: no aporta a la curva.',
 addReason='Cierra con más energía.',
 replaceReason='La 5 encaja mejor al inicio.',
 reorderReason='La curva de energía sube antes.',
 undoReason='El orden anterior servía mejor.',
 chatScript=`import io,json,re,sys,urllib.request
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
def answer_body(reply,actions,searches=None):
    body={'reply':reply,'actions':list(actions)}
    if searches is not None: body['searches']=list(searches)
    return json.dumps(body,ensure_ascii=False)
# The plain turn: one move, as before.
MOVE=answer_body("""${reply}""",[{'type':'move','position':1,'to':2,'reason':"""${reason}"""}])
# S4: the first answer of the search turn asks for one library search and proposes nothing.
SEARCH=answer_body('Busco en la biblioteca.',[],[{'query':''}])
# S5: the second answer proposes the five new changes against the list it just read.
FIVE=answer_body("""${searchReply}""",[
 {'type':'remove','position':3,'reason':"""${removeReason}"""},
 {'type':'add','ref':'L2','position':5,'reason':"""${addReason}"""},
 {'type':'replace_with','position':2,'ref':'L1','reason':"""${replaceReason}"""},
 {'type':'reorder','order':[4,1,2,3],'reason':"""${reorderReason}"""},
 {'type':'undo','reason':"""${undoReason}"""},
])
def fake(request,*,timeout):
    assert request.full_url==nan_client.DEFAULT_ENDPOINT
    assert request.get_header('Authorization')=='Bearer dummy-test-only'
    body=request.data.decode()
    # S3: one system message carries the list itself (the fixture tracks are titled
    # 'Electron test N', so their titles are the evidence the list was read) plus the
    # transitions, and never a local file path or a track identity (a sha256 hex id).
    assert str(root) not in body and 'fixtures/music' not in body
    assert 'Electron test 1' in body and 'Transiciones' in body
    assert not re.search(r'[0-9a-f]{64}',body)
    # S1: the chat instructions ask for the JSON object carrying the documented changes.
    system=json.loads(body)['messages'][0]
    assert system['role']=='system'
    assert 'JSON' in system['content'] and '"reply"' in system['content'] and '"actions"' in system['content'] and '"to"' in system['content']
    # One answer per request: a search round sends its second request with the local
    # results as the last message, and only that request carries the five changes.
    last=json.loads(body)['messages'][-1]['content']
    if last.startswith('Resultados de tu búsqueda'):
        assert '.flac' not in last
        assert not re.search(r'[0-9a-f]{64}',last)
        content=FIVE
    elif last=="""${searchRequest}""":
        content=SEARCH
    else:
        content=MOVE
    with (root/'fake-requests.jsonl').open('a') as log: log.write(json.dumps({'recipient':request.full_url,'body':body})+'\\n')
    return io.BytesIO(json.dumps({'choices':[{'message':{'content':content}}]}).encode())
backend.optional_ai.transport=fake
JsonlServer(backend,sys.stdout).run(sys.stdin.buffer)
`;
test('the chat surface and its proposed changes agree with the Python core',{skip:!python,timeout:60000},async()=>{
 const data=await realpath(await mkdtemp(path.join(os.tmpdir(),'xfin-chat-host-'))),credential=path.join(data,'selected.env'),requests=async()=>(await readFile(path.join(data,'fake-requests.jsonl'),'utf8')).trim().split('\n').length;
 await writeFile(credential,'NAN_API_KEY=dummy-test-only\n',{mode:0o600});
 const core=new PythonBridge(python,['-c',chatScript,data],{...process.env,PYTHONPATH:path.join(coreRoot,'src'),PYTHONDONTWRITEBYTECODE:'1',XFINAUDIO_AI_ENABLED:'1',NAN_API_BASE:'https://unapproved.invalid',NAN_API_KEY:'inherited-dummy-must-not-be-used'});
 const dialogs=[];
 const host=new OptionalAiHost({request:(method,params)=>core.request(method,params??{}),choose:async()=>null,confirm:async summary=>{dialogs.push(summary);return true;},cancel:()=>Promise.resolve({cancelled:false}),autoAuthorize:async()=>false,isClosing:()=>false});
 try{
  const initial=await core.request('ai.status');
  assert.deepEqual(await core.request('ai.chat.history'),{conversation:[],actions:[]},'a fresh core keeps an empty conversation and no changes');
  await core.request('library.scan',{root:path.join(coreRoot,'desktop-electron/tests/fixtures/music')});
  const review=await core.request('prep.generate',{targetTrackCount:4,name:'Chat host fixture'}),
   order=review.tracks.map(track=>track.id);
  assert.equal(order.length,4,'the fixture list has four tracks');
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
  assert.equal(turn.result.text,reply,'the reply is what the DJ reads');
  assert.ok(turn.result.text.length>=1&&turn.result.text.length<=4000,'the reply is 1 to 4000 characters');
  assert.deepEqual(turn.result.conversation.map(message=>message.role),['user','assistant']);
  assert.equal(turn.result.conversation[0].text,'¿Qué transiciones son las más débiles?');
  assert.equal(turn.result.conversation[1].text,reply,'only the reply text is stored');
  assert.equal(dialogs.length,1,'the first turn of a conversation is consented in the native dialog');
  // S2: one proposed change, named by position, title and artist, never by path or identity.
  assert.equal(turn.result.droppedActions,0,'the fake answer proposes one change that can apply');
  assert.equal(turn.result.actions.length,1);
  const [action]=turn.result.actions;
  assert.match(action.actionId,/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/,'the proposed change carries an opaque identity');
  assert.deepEqual(Object.keys(action).sort(),['actionId','artist','position','reason','title','to','type'],'a move publishes exactly its documented fields');
  assert.equal(action.type,'move');
  assert.equal(action.position,1);
  assert.equal(action.to,2);
  assert.equal(action.title,'Electron test 1');
  assert.equal(action.artist,'XfinAudio Test');
  assert.equal(action.reason,reason);
  assert.equal(/[0-9a-f]{64}/.test(JSON.stringify([action,turn.result.conversation,await core.request('ai.chat.history')])),false,'neither the answer nor the history publishes a track identity');
  assert.equal(JSON.stringify(turn.result).includes('fixtures'),false,'no local path crosses the boundary');
  const pending=await core.request('ai.chat.history');
  assert.deepEqual(pending.actions,[action],'the pending change is reported at its current position');
  assert.equal(pending.conversation.length,2,'the conversation keeps the turn');
  // S4 then S3: the bridge validates one opaque identity and the core applies it as an edit.
  const params=validateRequest('aiChatApply',{actionId:action.actionId});
  assert.deepEqual(params,{actionId:action.actionId});
  const applied=await core.request('ai.chat.apply',params);
  assert.notEqual(applied.review.reviewId,review.reviewId,'applying mints a new review identity');
  assert.deepEqual(applied.review.tracks.map(track=>track.id),[order[1],order[0],order[2],order[3]],'the applied move puts the first track in the second position');
  assert.equal(applied.review.canUndo,true,'the applied change is undoable like any manual edit');
  assert.deepEqual(applied.actions,[],'the applied change is no longer pending');
  assert.equal((await requests()),1,'applying never calls the provider');
  const afterApply=await core.request('ai.chat.history');
  assert.deepEqual(afterApply.actions,[],'the history no longer offers the applied change');
  assert.equal(afterApply.conversation.length,2,'applying keeps the conversation');
  const undone=await core.request('review.undo',{reviewId:applied.review.reviewId});
  assert.deepEqual(undone.tracks.map(track=>track.id),order,'undo restores the review order');
  assert.notEqual(undone.reviewId,applied.review.reviewId,'undo mints its own review identity');
  await assert.rejects(core.request('ai.chat.apply',params),error=>error.code==='stale_ai','an already applied identity is stale');
  const untouched=await core.request('review.details',{reviewId:undone.reviewId});
  assert.deepEqual(untouched.tracks.map(track=>track.id),order,'a stale apply changes nothing');
  const second=await host.prepare({surface:'chat',request:'¿Qué pista quitarías y por qué?',context:{reviewId:undone.reviewId}});
  assert.equal(second.firstTurn,false,'the stored conversation is no longer empty');
  const next=await host.ask(second.previewId);
  assert.equal(next.result.kind,'chat');
  assert.equal(next.result.listChanged,false,'the list is the one the last turn read');
  assert.equal(next.result.droppedActions,0);
  assert.equal(next.result.actions.length,1,'a new successful turn replaces the pending changes');
  assert.equal(next.result.actions[0].type,'move');
  assert.equal(next.result.actions[0].actionId!==action.actionId,true,'replaced changes get a fresh identity');
  assert.equal(dialogs.length,1,'a later turn of the same conversation reuses the first consent');
  assert.equal(await requests(),2,'only the two turns reached the provider');
  assert.deepEqual((await core.request('ai.chat.history')).conversation.map(message=>message.role),['user','assistant','user','assistant']);
  assert.deepEqual(await core.request('ai.chat.reset'),{conversation:[]});
  assert.deepEqual(await core.request('ai.chat.history'),{conversation:[],actions:[]},'reset clears the conversation and its changes');
  assert.equal((await host.prepare({surface:'chat',request:'Otra vez',context:{reviewId:untouched.reviewId}})).firstTurn,true,'reset starts a new conversation');
  // --- S4/S5/S6: one search round, then the five new changes, proven against the real core ---
  // A manual reorder gives the review an undo step, and S5 only proposes `undo` when one exists.
  const relisted=await core.request('review.reorder',{reviewId:untouched.reviewId,trackIds:[order[1],order[0],order[2],order[3]]});
  assert.deepEqual(relisted.tracks.map(track=>track.title),['Electron test 2','Electron test 1','Electron test 3','Electron test 4'],'the list the assistant reads next');
  assert.equal(relisted.canUndo,true,'the review now has an undo step to propose undoing');
  const asked=await host.prepare({surface:'chat',request:searchRequest,context:{reviewId:relisted.reviewId}});
  assert.equal(asked.firstTurn,true,'the reset conversation asks for consent again');
  const searched=await host.ask(asked.previewId);
  assert.equal(dialogs.length,2,'the new conversation is consented once');
  assert.equal(searched.cancelled,false);
  assert.equal(searched.result.text,searchReply,'only the final answer is what the DJ reads');
  assert.deepEqual(searched.result.conversation.map(message=>message.text),[searchRequest,searchReply],'the search answer is neither shown nor stored');
  assert.equal(searched.result.listChanged,false);
  assert.equal(searched.result.droppedActions,0,'every documented change can apply');
  const published=searched.result.actions;
  assert.deepEqual(published.map(action=>action.type),['remove','add','replace_with','reorder','undo'],'S5 publishes the five new changes');
  assert.equal(await requests(),4,'the search turn is exactly two provider requests');
  const bodies=(await readFile(path.join(data,'fake-requests.jsonl'),'utf8')).trim().split('\n').map(line=>JSON.parse(JSON.parse(line).body));
  const searching=bodies.filter(body=>body.messages.at(-1).content.startsWith('Resultados de tu búsqueda'));
  assert.equal(searching.length,1,'one search round, one extra request');
  const results=JSON.parse(searching[0].messages.at(-1).content.split('\n').at(-1));
  assert.deepEqual(results.map(result=>result.title),['Electron test 5','Electron test 6','Electron test 7','Electron test 8'],'the whole eligible library, closest BPM first');
  assert.deepEqual(results.map(result=>result.reference),['L1','L2','L3','L4'],'each result gets a conversation reference');
  for(const result of results){
   assert.deepEqual(Object.keys(result).sort(),['artist','bpm','duration','energy','genre','key','reference','title'],'a result carries no path and no track identity');
   assert.equal(/[0-9a-f]{64}/.test(JSON.stringify(result)),false);
  }
  const [removeCard,addCard,swapCard,orderCard,undoCard]=published;
  const library=(result,keys)=>Object.fromEntries(keys.map(key=>[key,result[key]]));
  assert.deepEqual(Object.keys(removeCard).sort(),['actionId','artist','position','reason','title','type'],'a remove publishes exactly its documented fields');
  assert.deepEqual([removeCard.position,removeCard.title,removeCard.artist,removeCard.reason],[3,'Electron test 3','XfinAudio Test',removeReason]);
  assert.deepEqual(Object.keys(addCard).sort(),['actionId','position','reason','track','type'],'an add publishes exactly its documented fields');
  assert.deepEqual([addCard.position,addCard.reason],[5,addReason]);
  assert.deepEqual(addCard.track,library(results[1],['title','artist','bpm','key']),'the added track is the one L2 named');
  assert.deepEqual(Object.keys(swapCard).sort(),['actionId','artist','position','reason','title','track','type'],'a replace_with publishes a remove plus the new track');
  assert.deepEqual([swapCard.position,swapCard.title,swapCard.reason],[2,'Electron test 1',replaceReason]);
  assert.deepEqual(swapCard.track,library(results[0],['title','artist','bpm','key']),'the replacing track is the one L1 named');
  assert.deepEqual(Object.keys(orderCard).sort(),['actionId','moved','reason','type'],'a reorder publishes how many tracks move');
  assert.deepEqual([orderCard.moved,orderCard.reason],[4,reorderReason]);
  assert.deepEqual(Object.keys(undoCard).sort(),['actionId','reason','type'],'an undo names nothing');
  assert.equal(undoCard.reason,undoReason);
  assert.equal(JSON.stringify(searched.result).includes('.flac'),false,'no local path leaves the core');
  assert.equal(/[0-9a-f]{64}/.test(JSON.stringify(searched.result)),false,'no track identity leaves the core');
  // The renderer's own validator and card text, fed with the actions the real core published.
  const history=await core.request('ai.chat.history');
  assert.deepEqual(history.actions,published,'the core reports the same pending changes');
  const unreachable=()=>{throw new Error('unreachable')};
  const panel=new ListChatController({aiChatHistory:async()=>history,aiChatReset:async()=>history,prepareAiRequest:unreachable,runAiRequest:unreachable,inspectAiPayload:unreachable,aiChatApply:unreachable},{canAct:()=>true,changed:()=>{},perform:async(_label,task,apply,fail)=>{try{apply(await task(),true);}catch(error){fail(error);}}});
  panel.setReview(relisted.reviewId);
  await panel.load();
  assert.equal(panel.error,'','the renderer accepts every change the core published');
  assert.deepEqual(panel.actions,published,'no change, field or bound was refused');
  assert.equal(panel.droppedActions,0);
  assert.deepEqual(panel.actions.map(listChatActionText),[
   'Quitar 3. Electron test 3',
   'Agregar Electron test 6 en la posición 5',
   'Reemplazar 2. Electron test 1 por Electron test 5',
   'Reordenar la lista (4 pistas cambian de lugar)',
   'Deshacer el último cambio',
  ],'every card renders its S6 sentence');
  // S5: each shown change applies as a normal review edit through the validated bridge request.
  const applyOnce=action=>core.request('ai.chat.apply',validateRequest('aiChatApply',{actionId:action.actionId}));
  const afterAdd=await applyOnce(addCard);
  assert.deepEqual(afterAdd.review.tracks.map(track=>track.title),['Electron test 2','Electron test 1','Electron test 3','Electron test 4','Electron test 6'],'the added track enters at its position');
  assert.deepEqual(afterAdd.actions.map(action=>action.type),['remove','replace_with','undo'],'the changes still pending stay bound to their tracks');
  const afterRemove=await applyOnce(removeCard);
  assert.deepEqual(afterRemove.review.tracks.map(track=>track.title),['Electron test 2','Electron test 1','Electron test 4','Electron test 6'],'the removed track leaves without a replacement');
  const afterSwap=await applyOnce(swapCard);
  assert.deepEqual(afterSwap.review.tracks.map(track=>track.title),['Electron test 2','Electron test 5','Electron test 4','Electron test 6'],'the swap replaces its track at its position');
  assert.deepEqual(afterSwap.actions.map(action=>action.type),['undo'],'a reorder bound to the old list is no longer offered');
  assert.equal(await requests(),4,'applying never calls the provider');
  const reverted=await core.request('review.undo',{reviewId:afterSwap.review.reviewId});
  assert.deepEqual(reverted.tracks.map(track=>track.title),['Electron test 2','Electron test 1','Electron test 4','Electron test 6'],'undo reverts the applied change');
 }finally{await core.close();await rm(data,{recursive:true,force:true});}
});
