import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {mkdtemp,mkdir,writeFile,symlink,realpath,rm} from 'node:fs/promises';
import os from 'node:os';import path from 'node:path';
const require=createRequire(import.meta.url);
const {SeratoHost}=require('../.out/main/serato-host.js');
const deferred=()=>{let resolve;return {promise:new Promise(r=>{resolve=r;}),resolve:v=>resolve(v)};};
async function fixture(overrides={}) {
 const temp=await realpath(await mkdtemp(path.join(os.tmpdir(),'xfin-serato-host-'))),root=path.join(temp,'_Serato_');await mkdir(path.join(root,'Subcrates'),{recursive:true});
 const calls=[];let closing=false;
 const summary={previewId:'preview',filename:'Set.crate',destinationLabel:'_Serato_',trackCount:2,readiness:'needs_review',warnings:['Review'],blockers:[],canCommit:true,backup:{required:true}};
 const receipt={receiptId:'receipt',filename:'Set.crate',destinationLabel:'_Serato_',trackCount:2,validated:true,backupCreated:true};
 const host=new SeratoHost({
  request:async(method,params)=>{calls.push([method,params]);if(method==='serato.registerDestination')return {destinationId:'dest',label:'_Serato_'};if(method==='serato.preview'||method==='serato.confirmation')return summary;if(method==='serato.commit')return receipt;if(method==='serato.receipt.resolve')return {path:path.join(root,'Subcrates','Set.crate')};throw new Error(method);},
  choose:async()=>root,confirm:async s=>{calls.push(['dialog',s]);return true;},reveal:p=>calls.push(['reveal',p]),isClosing:()=>closing,...overrides,
 });
 return {host,root,temp,calls,summary,receipt,setClosing:()=>{closing=true;},clean:()=>rm(temp,{recursive:true,force:true})};
}
test('native folder authority and exact preview feed a separate confirmation before commit',async()=>{
 const f=await fixture();try{await f.host.choose();await f.host.preview({source:{kind:'saved',playlistId:'42'},destinationId:'dest',name:'Set'});const result=await f.host.commit('preview');
 assert.equal(result,f.receipt);assert.deepEqual(f.calls[0],['serato.registerDestination',{seratoRoot:f.root}]);assert.equal(f.calls[1][1].source.playlistId,42);
 assert.deepEqual(f.calls.map(c=>c[0]),['serato.registerDestination','serato.preview','serato.confirmation','dialog','serato.commit']);assert.equal(f.calls[3][1].destinationPath,f.root);assert.deepEqual(f.calls[4][1],{previewId:'preview',confirmed:true});
 }finally{await f.clean();}
});
test('cancelled picker and final native confirmation never write',async()=>{
 const f=await fixture({choose:async()=>null,confirm:async()=>false});try{assert.equal(await f.host.choose(),null);assert.equal(f.calls.length,0);await assert.rejects(f.host.preview({source:{kind:'review',reviewId:'r'},destinationId:'unowned',name:'Set'}));assert.equal(f.calls.length,0);}finally{await f.clean();}
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
