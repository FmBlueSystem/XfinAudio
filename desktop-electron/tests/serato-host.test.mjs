import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {mkdtemp,mkdir,writeFile,symlink,realpath,rm,readFile} from 'node:fs/promises';
import os from 'node:os';import path from 'node:path';
const require=createRequire(import.meta.url);
const {SeratoHost,confirmationDetail}=require('../.out/main/serato-host.js');
const deferred=()=>{let resolve;return {promise:new Promise(r=>{resolve=r;}),resolve:v=>resolve(v)};};
async function fixture(overrides={}) {
 const temp=await realpath(await mkdtemp(path.join(os.tmpdir(),'xfin-serato-host-'))),root=path.join(temp,'_Serato_');await mkdir(path.join(root,'Subcrates'),{recursive:true});
 const calls=[];let closing=false;
 const summary={previewId:'preview',filename:'Set.crate',destinationLabel:'_Serato_',trackCount:2,readiness:'needs_review',warnings:['Review'],blockers:[],canCommit:true,backup:{required:true}};
 const receipt={receiptId:'receipt',filename:'Set.crate',destinationLabel:'_Serato_',trackCount:2,validated:true,backupCreated:true};
 const host=new SeratoHost({
  request:async(method,params)=>{calls.push([method,params]);if(method==='serato.suggestDestination')return {suggestion:null};if(method==='serato.registerDestination')return {destinationId:'dest',label:'_Serato_'};if(method==='serato.preview'||method==='serato.confirmation')return summary;if(method==='serato.commit')return receipt;if(method==='serato.receipt.resolve')return {path:path.join(root,'Subcrates','Set.crate')};throw new Error(method);},
  choose:async()=>root,confirm:async s=>{calls.push(['dialog',s]);return true;},reveal:p=>calls.push(['reveal',p]),isClosing:()=>closing,...overrides,
 });
 return {host,root,temp,calls,summary,receipt,setClosing:()=>{closing=true;},clean:()=>rm(temp,{recursive:true,force:true})};
}
test('native folder authority and exact preview feed a separate confirmation before commit',async()=>{
 const f=await fixture();try{await f.host.choose();await f.host.preview({source:{kind:'saved',playlistId:'42'},destinationId:'dest',name:'Set'});const result=await f.host.commit('preview');
 assert.equal(result,f.receipt);assert.deepEqual(f.calls[1],['serato.registerDestination',{seratoRoot:f.root}]);assert.equal(f.calls[2][1].source.playlistId,42);
 assert.deepEqual(f.calls.map(c=>c[0]),['serato.suggestDestination','serato.registerDestination','serato.preview','serato.confirmation','dialog','serato.commit']);assert.equal(f.calls[4][1].destinationPath,f.root);assert.deepEqual(f.calls[5][1],{previewId:'preview',confirmed:true});
 }finally{await f.clean();}
});
test('cancelled picker and final native confirmation never write',async()=>{
 const f=await fixture({choose:async()=>null,confirm:async()=>false});try{assert.equal(await f.host.choose(),null);assert.equal(f.calls.length,1);await assert.rejects(f.host.preview({source:{kind:'review',reviewId:'r'},destinationId:'unowned',name:'Set'}));assert.equal(f.calls.length,1);}finally{await f.clean();}
 const g=await fixture({confirm:async()=>false});try{await g.host.choose();await g.host.preview({source:{kind:'review',reviewId:'r'},destinationId:'dest',name:'Set'});assert.deepEqual(await g.host.commit('preview'),{cancelled:true});assert.equal(g.calls.some(c=>c[0]==='serato.commit'),false);}finally{await g.clean();}
});
test('close during native confirmation blocks publication and duplicate clicks are rejected',async()=>{
 const answer=deferred(),f=await fixture({confirm:()=>answer.promise});try{await f.host.choose();await f.host.preview({source:{kind:'review',reviewId:'r'},destinationId:'dest',name:'Set'});const pending=f.host.commit('preview');await new Promise(r=>setImmediate(r));assert.equal(f.host.busy,true);await assert.rejects(f.host.commit('preview'));f.setClosing();answer.resolve(true);await assert.rejects(pending);assert.equal(f.calls.some(c=>c[0]==='serato.commit'),false);}finally{await f.clean();}
});
test('shutdown waits for noncancellable publication completion, including rejection',async()=>{
 for(const fail of [false,true]){const result=deferred(),f=await fixture();const original=f.host;let writing=false;
  original.dependencies.request=async(method)=>{if(method==='serato.registerDestination')return {destinationId:'dest',label:'_Serato_'};if(method==='serato.preview'||method==='serato.confirmation')return f.summary;if(method==='serato.commit'){writing=true;await result.promise;if(fail)throw new Error('write failed');return f.receipt;}};
  try{await original.choose();await original.preview({source:{kind:'review',reviewId:'r'},destinationId:'dest',name:'Set'});const pending=original.commit('preview').catch(e=>e);await new Promise(r=>setImmediate(r));assert.equal(writing,true);let drained=false;const drain=original.waitForCommit().then(()=>{drained=true;});await new Promise(r=>setImmediate(r));assert.equal(drained,false);result.resolve();await pending;await drain;assert.equal(drained,true);}finally{await f.clean();}
 }
});
test('reveal accepts only committed receipt and unchanged regular crate under authorized Subcrates',async()=>{
 const f=await fixture();try{await assert.rejects(f.host.reveal('unknown'));await f.host.choose();await f.host.preview({source:{kind:'review',reviewId:'r'},destinationId:'dest',name:'Set'});await f.host.commit('preview');const file=path.join(f.root,'Subcrates','Set.crate');await writeFile(file,'fixture');await f.host.reveal('receipt');assert.deepEqual(f.calls.at(-1),['reveal',file]);await rm(file);await writeFile(path.join(f.temp,'other.crate'),'other');await symlink(path.join(f.temp,'other.crate'),file);await assert.rejects(f.host.reveal('receipt'));}finally{await f.clean();}
});
test('auto-detected _Serato_ registers without opening the picker',async()=>{
 const temp=await realpath(await mkdtemp(path.join(os.tmpdir(),'xfin-serato-host-'))),root=path.join(temp,'_Serato_');await mkdir(path.join(root,'Subcrates'),{recursive:true});
 const calls=[];
 const host=new SeratoHost({request:async(method,params)=>{calls.push([method,params]);
  if(method==='serato.suggestDestination')return {suggestion:root};
  if(method==='serato.registerDestination')return {destinationId:'dest',label:'_Serato_'};
  throw new Error(method);},
  choose:async()=>{throw new Error('picker must not open');},confirm:async()=>true,reveal:()=>{},isClosing:()=>false});
 try{const result=await host.choose();
  assert.deepEqual(result,{destinationId:'dest',label:'_Serato_'});
  assert.deepEqual(calls.map(c=>c[0]),['serato.suggestDestination','serato.registerDestination']);
 }finally{await rm(temp,{recursive:true,force:true});}
});
test('a null suggestion still opens the picker as the honest fallback',async()=>{
 const f=await fixture({request:async(method,params)=>{f.calls.push([method,params]);
  if(method==='serato.suggestDestination')return {suggestion:null};
  if(method==='serato.registerDestination')return {destinationId:'dest',label:'_Serato_'};
  throw new Error(method);}});
 try{const result=await f.host.choose();
  assert.deepEqual(result,{destinationId:'dest',label:'_Serato_'});
  assert.deepEqual(f.calls.map(c=>c[0]),['serato.suggestDestination','serato.registerDestination']);
 }finally{await f.clean();}
});
test('detection registers the discovered _Serato_ folder without touching the picker',async()=>{
 const temp=await realpath(await mkdtemp(path.join(os.tmpdir(),'xfin-serato-host-'))),root=path.join(temp,'_Serato_');await mkdir(path.join(root,'Subcrates'),{recursive:true});
 const calls=[];
 const host=new SeratoHost({request:async(method,params)=>{calls.push([method,params]);
  if(method==='serato.suggestDestination')return {suggestion:root};
  if(method==='serato.registerDestination')return {destinationId:'dest',label:'_Serato_ · dd'};
  throw new Error(method);},
  choose:async()=>{throw new Error('picker must not open');},confirm:async()=>true,reveal:()=>{},isClosing:()=>false});
 try{assert.deepEqual(await host.detect(),{destinationId:'dest',label:'_Serato_ · dd'});
  assert.deepEqual(calls.map(c=>c[0]),['serato.suggestDestination','serato.registerDestination']);
  assert.deepEqual(calls[1][1],{seratoRoot:root});
 }finally{await rm(temp,{recursive:true,force:true});}
});
test('detection with no candidate answers null and never opens the picker',async()=>{
 const calls=[];
 const host=new SeratoHost({request:async(method,params)=>{calls.push([method,params]);
  if(method==='serato.suggestDestination')return {suggestion:null};
  throw new Error(method);},
  choose:async()=>{throw new Error('picker must not open');},confirm:async()=>true,reveal:()=>{},isClosing:()=>false});
 assert.equal(await host.detect(),null);
 assert.deepEqual(calls.map(c=>c[0]),['serato.suggestDestination']);
});
test('detection reports a failed discovery instead of guessing a destination',async()=>{
 const host=new SeratoHost({request:async(method)=>{if(method==='serato.suggestDestination')throw Object.assign(new Error('[core_stopped] gone'),{code:'core_stopped'});throw new Error(method);},
  choose:async()=>{throw new Error('picker must not open');},confirm:async()=>true,reveal:()=>{},isClosing:()=>false});
 await assert.rejects(host.detect(),error=>error.code==='core_stopped');
});
test('a chosen drive folder exports into the _Serato_ folder it directly contains',async()=>{
 const temp=await realpath(await mkdtemp(path.join(os.tmpdir(),'xfin-serato-host-')));
 const drive=path.join(temp,'dd'),inner=path.join(drive,'_Serato_');await mkdir(path.join(inner,'Subcrates'),{recursive:true});
 await mkdir(path.join(drive,'_Lossless','por_genero'),{recursive:true});
 const calls=[];
 const host=new SeratoHost({request:async(method,params)=>{calls.push([method,params]);
  if(method==='serato.suggestDestination')return {suggestion:null};
  if(method==='serato.registerDestination')return {destinationId:'dest',label:'_Serato_ · dd'};
  throw new Error(method);},
  choose:async()=>drive,confirm:async()=>true,reveal:()=>{},isClosing:()=>false});
 try{assert.deepEqual(await host.detect(),null);
  assert.deepEqual(await host.choose(),{destinationId:'dest',label:'_Serato_ · dd'});
  assert.deepEqual(calls.at(-1),['serato.registerDestination',{seratoRoot:inner}],'the inner _Serato_ folder is the destination');
 }finally{await rm(temp,{recursive:true,force:true});}
});
test('a chosen folder without Subcrates keeps the existing invalid_destination refusal',async()=>{
 const temp=await realpath(await mkdtemp(path.join(os.tmpdir(),'xfin-serato-host-')));
 const drive=path.join(temp,'dd');await mkdir(path.join(drive,'_Serato_'),{recursive:true});
 const calls=[];
 const host=new SeratoHost({request:async(method,params)=>{calls.push([method,params]);
  if(method==='serato.suggestDestination')return {suggestion:null};
  if(method==='serato.registerDestination')throw Object.assign(new Error('[invalid_destination] Choose an existing _Serato_ folder containing Subcrates'),{code:'invalid_destination'});
  throw new Error(method);},
  choose:async()=>drive,confirm:async()=>true,reveal:()=>{},isClosing:()=>false});
 try{await assert.rejects(host.choose(),error=>error.code==='invalid_destination');
  assert.deepEqual(calls.at(-1),['serato.registerDestination',{seratoRoot:drive}],'an unusable inner folder is never invented');
 }finally{await rm(temp,{recursive:true,force:true});}
});

test('quick export reuses the session destination, previews once, confirms natively and commits',async()=>{
 const f=await fixture();try{
  await f.host.choose();f.calls.length=0;
  const result=await f.host.quickExport({source:{kind:'saved',playlistId:'42'},name:'Set'});
  assert.deepEqual(result,{status:'exported',receipt:f.receipt});
  assert.deepEqual(f.calls.map(c=>c[0]),['serato.preview','serato.confirmation','dialog','serato.commit'],'one click never discovers or previews twice');
  assert.equal(f.calls[0][1].destinationId,'dest');assert.equal(f.calls[0][1].source.playlistId,42);assert.equal(f.calls[0][1].name,'Set');
  assert.deepEqual(f.calls.at(-1)[1],{previewId:'preview',confirmed:true});
 }finally{await f.clean();}
});
test('quick export detects the destination when the session has none and never opens the picker',async()=>{
 const temp=await realpath(await mkdtemp(path.join(os.tmpdir(),'xfin-serato-host-'))),root=path.join(temp,'_Serato_');await mkdir(path.join(root,'Subcrates'),{recursive:true});
 const calls=[];let dialogs=0;
 const summary={previewId:'preview',filename:'Set.crate',destinationLabel:'_Serato_ · dd',trackCount:2,readiness:'ready',warnings:[],blockers:[],canCommit:true,backup:{required:false}};
 const receipt={receiptId:'receipt',filename:'Set.crate',destinationLabel:'_Serato_ · dd',trackCount:2,validated:true,backupCreated:false};
 const host=new SeratoHost({request:async(method,params)=>{calls.push([method,params]);
  if(method==='serato.suggestDestination')return {suggestion:root};
  if(method==='serato.registerDestination')return {destinationId:'dest',label:'_Serato_ · dd'};
  if(method==='serato.preview'||method==='serato.confirmation')return summary;
  if(method==='serato.commit')return receipt;throw new Error(method);},
  choose:async()=>{throw new Error('picker must not open');},confirm:async()=>{dialogs++;return true;},reveal:()=>{},isClosing:()=>false});
 try{
  assert.deepEqual(await host.quickExport({source:{kind:'review',reviewId:'r'},name:'Set'}),{status:'exported',receipt});
  assert.deepEqual(calls.map(c=>c[0]),['serato.suggestDestination','serato.registerDestination','serato.preview','serato.confirmation','serato.commit']);
  assert.deepEqual(calls[1][1],{seratoRoot:root});assert.equal(dialogs,1);
 }finally{await rm(temp,{recursive:true,force:true});}
});
test('quick export with nothing to detect answers a typed result and never opens a dialog',async()=>{
 const calls=[];let dialogs=0;
 const host=new SeratoHost({request:async(method,params)=>{calls.push([method,params]);if(method==='serato.suggestDestination')return {suggestion:null};throw new Error(method);},
  choose:async()=>{throw new Error('picker must not open');},confirm:async()=>{dialogs++;return true;},reveal:()=>{},isClosing:()=>false});
 assert.deepEqual(await host.quickExport({source:{kind:'review',reviewId:'r'},name:'Set'}),{status:'needs_destination'});
 assert.deepEqual(calls.map(c=>c[0]),['serato.suggestDestination']);assert.equal(dialogs,0);
});
test('a blocked quick export returns the blockers without a dialog or a write',async()=>{
 const blocked={previewId:'preview',filename:'Set.crate',destinationLabel:'_Serato_',trackCount:2,readiness:'blocked',warnings:['Aviso'],blockers:['All tracks and the selected Serato folder must belong to the same source volume'],canCommit:false,backup:{required:false}};
 let dialogs=0;
 const f=await fixture({request:async(method,params)=>{f.calls.push([method,params]);
  if(method==='serato.suggestDestination')return {suggestion:null};
  if(method==='serato.registerDestination')return {destinationId:'dest',label:'_Serato_'};
  if(method==='serato.preview'||method==='serato.confirmation')return blocked;
  throw new Error(`must not ${method}`);},confirm:async()=>{dialogs++;return true;}});
 try{
  await f.host.choose();
  assert.deepEqual(await f.host.quickExport({source:{kind:'review',reviewId:'r'},name:'Set'}),{status:'blocked',filename:'Set.crate',blockers:[blocked.blockers[0]]});
  assert.equal(dialogs,0);assert.equal(f.calls.some(c=>c[0]==='serato.commit'),false);
 }finally{await f.clean();}
});
test('a cancelled quick export dialog writes nothing and reports the cancellation',async()=>{
 const f=await fixture({confirm:async()=>false});try{
  await f.host.choose();
  assert.deepEqual(await f.host.quickExport({source:{kind:'review',reviewId:'r'},name:'Set'}),{status:'cancelled'});
  assert.equal(f.calls.some(c=>c[0]==='serato.commit'),false);
 }finally{await f.clean();}
});
test('the native confirmation detail carries the crate name, destination, count, replacement line and warnings',async()=>{
 const f=await fixture();try{
  await f.host.choose();await f.host.quickExport({source:{kind:'review',reviewId:'r'},name:'Set'});
  const summary=f.calls.find(c=>c[0]==='dialog')[1];
  const detail=confirmationDetail(summary);
  assert.ok(detail.includes(path.join(f.root,'Subcrates','Set.crate')),'the exact crate path must be shown');
  assert.match(detail,/2 pistas en el orden revisado/);
  assert.match(detail,/Se reemplazará el crate existente y se conservará una copia de seguridad\./);
  assert.match(detail,/Review/);
  assert.match(confirmationDetail({...summary,backup:{required:false}}),/Se creará un crate nuevo\./);
  const main=await readFile(new URL('../src/main.ts',import.meta.url),'utf8');
  assert.match(main,/const detail=confirmationDetail\(summary\)/,'main must build the dialog from the shared detail');
  assert.match(main,/\{type:'warning',title:'Confirmar exportación a Serato',message:`¿Exportar \$\{summary\.filename\}\?`,detail,buttons:\['Cancelar','Exportar a Serato'\]/,'the one native consent uses that detail');
 }finally{await f.clean();}
});
