import test from 'node:test';import assert from 'node:assert/strict';import {mkdtemp,realpath,rm,readFile,readdir} from 'node:fs/promises';import {createHash,randomUUID} from 'node:crypto';import {createRequire} from 'node:module';import path from 'node:path';import os from 'node:os';import {fileURLToPath} from 'node:url';
const require=createRequire(import.meta.url),{PythonBridge}=require('../.out/main/bridge.js');const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..'),music=path.join(root,'desktop-electron/tests/fixtures/music'),python=process.env.XFIN_PYTHON;
const hash=async file=>createHash('sha256').update(await readFile(file)).digest('hex');
test('real ready-only Live resumes, advances once, preserves exact pool and invalidates after scan',{skip:!python,timeout:30000},async()=>{
 const data=await realpath(await mkdtemp(path.join(os.tmpdir(),'xfin-live-')));const core=new PythonBridge(python,['-m','xfinaudio.headless','--data-dir',data],{...process.env,PYTHONPATH:path.join(root,'src')});
 const files=(await readdir(music)).map(name=>path.join(music,name)),before=await Promise.all(files.map(hash));
 try {
  await core.request('library.scan',{root:music});const review=await core.request('prep.generate',{targetTrackCount:4,strategy:'harmonic_journey'});assert.equal(review.readiness,'ready');
  let state=await core.request('live.open',{reviewId:review.reviewId});assert.equal(state.current.id,review.tracks[0].id);assert.equal(state.revision,0);assert.equal(JSON.stringify(state).includes(music),false);
  const first=state,currentIds=[first.current.id];const jobId=randomUUID();const pending=core.request('live.next',{sessionId:state.sessionId,revision:state.revision,trackId:state.candidates[0].track.id},jobId);assert.equal((await core.request('cancel',{jobId})).cancelled,false);state=await pending;currentIds.push(state.current.id);
  const resumed=await core.request('live.open',{reviewId:review.reviewId});assert.equal(resumed.sessionId,state.sessionId);assert.equal(resumed.revision,1);
  await assert.rejects(core.request('live.next',{sessionId:state.sessionId,revision:0,trackId:state.current.id}),error=>error.code==='stale_live');
  while(state.candidates.length){state=await core.request('live.next',{sessionId:state.sessionId,revision:state.revision,trackId:state.candidates[0].track.id});currentIds.push(state.current.id);}
  assert.equal(state.state,'complete');assert.equal(state.history.length,3);assert.deepEqual(new Set(currentIds),new Set(review.tracks.map(t=>t.id)));
  await core.request('library.scan',{root:music});await assert.rejects(core.request('live.status',{sessionId:state.sessionId}),error=>error.code==='stale_live');assert.deepEqual(await Promise.all(files.map(hash)),before);
 }finally{await core.close();await rm(data,{recursive:true,force:true});}
});
