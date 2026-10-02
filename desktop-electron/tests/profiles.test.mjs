import test from 'node:test';
import assert from 'node:assert/strict';
const status=(patch={})=>({state:'partial',totalTracks:2,readyCount:1,spectralReadyCount:2,danceabilityReadyCount:1,edgeReadyCount:1,pendingCount:1,failedCount:1,...patch});
test('profile status validates truthful bounded aggregate state and strips unrelated fields',async()=>{
  const {profileStatus}=await import('../.out/renderer/profiles.js');assert.deepEqual(profileStatus({...status(),path:'/private'}),status());
  for(const patch of [{state:'ready'},{readyCount:3},{pendingCount:0},{failedCount:-1},{edgeReadyCount:.5},{totalTracks:Infinity},{state:'complete'},{readyCount:2,edgeReadyCount:1,pendingCount:0}])assert.throws(()=>profileStatus(status(patch)));
  for(const state of ['partial','cancelled','unavailable'])assert.equal(profileStatus(status({state})).state,state);
});
test('cohesion settings stay local/dirty until revision-bound save and survive navigation or conflict',async()=>{
  const {ProfileSettingsController}=await import('../.out/renderer/profile-settings.js');const calls=[],dirty=[],applied=[];let stale=false,busy=false;
  const controller=new ProfileSettingsController({getProfileSettings:async()=>({revision:'a'.repeat(64),spectralCohesion:.5}),saveProfileSettings:async params=>{calls.push(params);if(stale)throw Error('[stale_settings] /secret');return {...params,revision:'b'.repeat(64)};}},{canAct:()=>!busy,changed:()=>{},dirtyChanged:value=>dirty.push(value),applied:()=>applied.push(true),perform:async(_label,task,apply,failure)=>{busy=true;try{apply(await task());}catch(error){failure(error);}finally{busy=false;}}});
  await controller.load();assert.equal(controller.snapshot.spectralCohesion,.5);controller.setCohesion(.8);assert.equal(controller.dirty,true);assert.deepEqual(calls,[]);assert.equal(applied.length,0);await controller.load();assert.equal(controller.snapshot.spectralCohesion,.8);await controller.save();assert.deepEqual(calls,[{revision:'a'.repeat(64),spectralCohesion:.8}]);assert.equal(controller.dirty,false);assert.equal(applied.length,1);
  controller.setCohesion(.2);stale=true;await controller.save();assert.equal(controller.snapshot.spectralCohesion,.2);assert.equal(controller.canSave,false);assert.match(controller.error,/descarta.*actualiza/i);assert.doesNotMatch(controller.error,/secret|stale_settings/);controller.discard();assert.equal(controller.dirty,false);await controller.load();assert.equal(controller.snapshot.spectralCohesion,.5);assert.equal(dirty.at(-1),false);
  for(const value of [NaN,Infinity,-1,2,'0.4',null])controller.setCohesion(value);assert.equal(controller.snapshot.spectralCohesion,.5);
});
test('unavailable summary does not claim unavailable engines when silent or unreadable excerpts may be the cause',async()=>{const {profileSummary}=await import('../.out/renderer/profiles.js');const summary=profileSummary(status({state:'unavailable'}),false,false);assert.match(summary,/^Perfiles no disponibles/);assert.doesNotMatch(summary,/Motores/);});
