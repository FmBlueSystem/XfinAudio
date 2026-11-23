import test from 'node:test';
import assert from 'node:assert/strict';
const status=(patch={})=>{const value={state:'partial',totalTracks:2,readyCount:1,spectralReadyCount:2,danceabilityReadyCount:1,edgeReadyCount:1,pendingCount:1,failedCount:1,estimatedRemainingSeconds:null,...patch};return {...value,spectralPendingCount:value.totalTracks-value.spectralReadyCount,danceabilityPendingCount:value.totalTracks-value.danceabilityReadyCount,edgePendingCount:value.totalTracks-value.edgeReadyCount-(value.edgeNotApplicableCount??0),edgeNotApplicableCount:value.edgeNotApplicableCount??0};};
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
test('a separate not-applicable count keeps short tracks out of edges and is shown in Spanish only above zero',async()=>{
  const {profileStatus,profileSummary,profileShortTracksLabel}=await import('../.out/renderer/profiles.js');
  const short={state:'complete',totalTracks:4,readyCount:4,spectralReadyCount:4,danceabilityReadyCount:4,edgeReadyCount:3,edgeNotApplicableCount:1,spectralPendingCount:0,danceabilityPendingCount:0,edgePendingCount:0,pendingCount:0,failedCount:0,estimatedRemainingSeconds:0};
  assert.deepEqual(profileStatus(short),short);
  assert.equal(profileShortTracksLabel(1),'1 no aplican (menos de 65 s)');
  assert.equal(profileShortTracksLabel(32),'32 no aplican (menos de 65 s)');
  assert.equal(profileShortTracksLabel(0),'');
  assert.match(profileSummary(short,false,false),/1 no aplican \(menos de 65 s\)/);
  const noShortTracks={...short,edgeReadyCount:4,edgeNotApplicableCount:0};
  assert.doesNotMatch(profileSummary(noShortTracks,false,false),/no aplican/);
  // Backward compatibility: a payload that predates the field still validates, as zero.
  const {edgeNotApplicableCount:omitted,...legacy}={...short,edgePendingCount:1};
  assert.equal(profileStatus(legacy).edgeNotApplicableCount,0);
  // The edge halves plus the not-applicable tracks still add up to the library.
  for(const patch of [{edgePendingCount:1},{edgeNotApplicableCount:-1},{edgeNotApplicableCount:.5},{edgeNotApplicableCount:5,readyCount:4,edgeReadyCount:3,pendingCount:0}])
    assert.throws(()=>profileStatus({...short,...patch}));
});

test('unavailable summary does not claim unavailable engines when silent or unreadable excerpts may be the cause',async()=>{const {profileSummary}=await import('../.out/renderer/profiles.js');const summary=profileSummary(status({state:'unavailable'}),false,false);assert.match(summary,/^Perfiles no disponibles/);assert.doesNotMatch(summary,/Motores/);});
test('summary names the pending tracks per analysis and the measured remaining time in Spanish',async()=>{
  const {profileStatus,profileSummary,profileEta}=await import('../.out/renderer/profiles.js');
  const value={state:'partial',totalTracks:4,readyCount:1,spectralReadyCount:4,danceabilityReadyCount:1,edgeReadyCount:1,spectralPendingCount:0,danceabilityPendingCount:3,edgePendingCount:3,edgeNotApplicableCount:0,pendingCount:3,failedCount:0,estimatedRemainingSeconds:12000};
  assert.deepEqual(profileStatus({...value,path:'/private'}),value);
  const summary=profileSummary(value,false,false);assert.match(summary,/Pendientes por análisis: espectral 0 · bailabilidad 3 · bordes 3\./);assert.match(summary,/Faltan unas 3 h 20 min\./);
  assert.doesNotMatch(profileSummary({...value,estimatedRemainingSeconds:null},false,false),/Faltan/);
  assert.match(profileSummary(value,false,false,600),/Faltan unos 10 min/);
  assert.equal(profileEta(null),'');assert.equal(profileEta(0),'');assert.equal(profileEta(30),'Falta menos de un minuto');assert.equal(profileEta(600),'Faltan unos 10 min');assert.equal(profileEta(3600),'Falta 1 h');assert.equal(profileEta(12000),'Faltan unas 3 h 20 min');
  for(const patch of [{spectralPendingCount:1},{danceabilityPendingCount:-1},{edgePendingCount:.5},{estimatedRemainingSeconds:-1},{estimatedRemainingSeconds:'600'},{estimatedRemainingSeconds:60,pendingCount:0,readyCount:4,spectralReadyCount:4,danceabilityReadyCount:4,edgeReadyCount:4,spectralPendingCount:0,danceabilityPendingCount:0,edgePendingCount:0}])
    assert.throws(()=>profileStatus({...value,...patch}));
});
