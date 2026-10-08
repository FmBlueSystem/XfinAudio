import test from 'node:test';import assert from 'node:assert/strict';import {createRequire} from 'node:module';import {mkdtemp,realpath,mkdir,writeFile,rm,symlink} from 'node:fs/promises';import os from 'node:os';import path from 'node:path';
const require=createRequire(import.meta.url),{OptionalAiHost}=require('../.out/main/optional-ai-host.js'),{validateRequest}=require('../.out/main/security.js');
const id='11111111-1111-4111-8111-111111111111',rev='a'.repeat(64),recipient='https://api.nan.builders/v1/chat/completions',deferred=()=>{let resolve;return {promise:new Promise(r=>resolve=r),resolve:v=>resolve(v)}};
function fixture(){const calls=[];let choose=async()=>null,confirm=async()=>true,closing=false,endpoint=recipient,auto=false;const host=new OptionalAiHost({request:async(method,params)=>{calls.push([method,params]);if(method==='ai.prepare'||method==='ai.confirmation')return {previewId:id,surface:'editor',recipient:endpoint,disclosure:['Solicitud sin pistas'],requestPreview:'Acorta a 2 temas'};if(method==='ai.run')return {cancelled:false,result:{resultId:id}};return {revision:rev};},choose:()=>choose(),confirm:summary=>{calls.push(['dialog',summary]);return confirm();},cancel:async()=>{calls.push(['cancel']);return {cancelled:true};},autoAuthorize:async()=>auto,isClosing:()=>closing});return {host,calls,setChoose:v=>choose=v,setConfirm:v=>confirm=v,setAuto:v=>auto=v,close:()=>closing=true,badEndpoint:()=>endpoint='https://elsewhere.example'};}
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
