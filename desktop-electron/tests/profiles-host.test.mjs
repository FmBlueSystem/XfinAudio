import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {validateRequest}=require('../.out/main/security.js');
test('profile IPC is empty/status-only or bounded revisioned cohesion, never paths or commands',()=>{
  for(const method of ['getProfileStatus','completeProfiles','getProfileSettings']){assert.deepEqual(validateRequest(method),{});for(const params of [{root:'/private'},{trackIds:[]},{command:'analyze'},{force:true}])assert.throws(()=>validateRequest(method,params));}
  const good={revision:'a'.repeat(64),spectralCohesion:.5};assert.deepEqual(validateRequest('saveProfileSettings',good),good);
  for(const value of [NaN,Infinity,-.1,1.1,'0.5',null])assert.throws(()=>validateRequest('saveProfileSettings',{...good,spectralCohesion:value}));
  for(const params of [{...good,revision:'bad'},{...good,enabled:true},{}])assert.throws(()=>validateRequest('saveProfileSettings',params));
  assert.throws(()=>validateRequest('profiles.complete',{}));
});
test('profile host remains exclusive through cancellation and drains active work before close',async()=>{
  const {ProfilesHost}=require('../.out/main/profiles-host.js');let finish,cancelled=0,closing=false;const calls=[];
  const host=new ProfilesHost({request:async(method,params)=>{calls.push([method,params]);return new Promise(resolve=>finish=resolve);},cancel:async()=>{cancelled++;},isClosing:()=>closing});
  const work=host.complete();assert.equal(host.busy,true);await assert.rejects(host.complete(),/busy/);assert.equal((await host.cancel()).cancelled,true);assert.equal(host.busy,true);
  let stopped=false;closing=true;const stop=host.shutdown().then(()=>stopped=true);await new Promise(resolve=>setImmediate(resolve));assert.equal(stopped,false);assert.equal(cancelled,2);finish({cancelled:true});await work;await stop;assert.equal(host.busy,false);await assert.rejects(host.complete(),/core_stopped/);assert.deepEqual(calls,[['profiles.complete',{}]]);
});
test('profile host failure releases the gate and progress projects bounded safe fields only',async()=>{
  const {ProfilesHost,profileProgress}=require('../.out/main/profiles-host.js');const host=new ProfilesHost({request:async()=>{throw Error('failure');},cancel:async()=>{},isClosing:()=>false});await assert.rejects(host.complete());assert.equal(host.busy,false);assert.deepEqual(await host.cancel(),{cancelled:false});
  const valid={phase:'profiles',stage:'spectral',processedCount:2,totalCount:4,readyCount:2,failedCount:0};assert.deepEqual(profileProgress({...valid,fileName:'/private',message:'raw error',path:'/music'}),valid);
  for(const patch of [{stage:'private'},{processedCount:5},{totalCount:-1},{readyCount:NaN},{failedCount:1.2},{phase:'other'}])assert.equal(profileProgress({...valid,...patch}),null);
});
