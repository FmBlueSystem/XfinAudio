import test from 'node:test';import assert from 'node:assert/strict';import {mkdtemp,mkdir,rm,readFile,readdir,realpath,symlink,writeFile} from 'node:fs/promises';import {createHash} from 'node:crypto';import {createRequire} from 'node:module';import {execFileSync} from 'node:child_process';import path from 'node:path';import {fileURLToPath} from 'node:url';
const require=createRequire(import.meta.url),{PythonBridge}=require('../.out/main/bridge.js'),root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..'),python=process.env.XFIN_PYTHON;
test('real FFmpeg loudness writes owned FLAC metadata with exact backup and unchanged decoded audio',{skip:!python,timeout:30000},async()=>{
 const data=await realpath(await mkdtemp(path.join(process.env.XFIN_TEST_TMPDIR??'/tmp','xfin-loudness-'))),music=path.join(data,'music'),audio=path.join(music,'owned-65s.flac');await mkdir(music);
 const source=path.join(root,'tests/fixtures/loudness/synthetic_tone_1khz.wav'),sourceBefore=await readFile(source);
 execFileSync('ffmpeg',['-nostdin','-hide_banner','-loglevel','error','-stream_loop','-1','-i',source,'-t','65','-c:a','flac',audio]);
 const pcm=()=>createHash('sha256').update(execFileSync('ffmpeg',['-nostdin','-hide_banner','-loglevel','error','-i',audio,'-map','0:a:0','-f','s16le','-'],{maxBuffer:32*1024*1024})).digest('hex');
 const before=await readFile(audio),decoded=pcm();const core=new PythonBridge(python,['-m','xfinaudio.headless','--data-dir',data],{...process.env,PYTHONPATH:path.join(root,'src')});
 try{
  const scanned=await core.request('library.scan',{root:music});assert.equal(scanned.tracks.length,1);
  const status=await core.request('loudness.status');assert.equal(status.available,true);assert.equal(status.tracks[0].state,'unmeasured');
  const preview=await core.request('loudness.preview',{trackIds:[scanned.tracks[0].id],force:false});assert.deepEqual(await readFile(audio),before);
  const result=await core.request('loudness.run',{previewId:preview.previewId,confirmed:true});assert.equal(result.changedCount,1);assert.equal(result.backupCount,1);assert.equal(result.failureCount,0);assert.equal(result.warning,null);assert.equal(result.status.tracks[0].complete,true);assert.ok(Number.isFinite(result.status.tracks[0].lufs));assert.equal(pcm(),decoded);
  const run=(await readdir(path.join(data,'loudness-backups')))[0],files=(await readdir(path.join(data,'loudness-backups',run))).filter(name=>name.endsWith('.bak'));assert.equal(files.length,1);assert.deepEqual(await readFile(path.join(data,'loudness-backups',run,files[0])),before);
  const again=await core.request('loudness.preview',{trackIds:[scanned.tracks[0].id],force:false});const cached=await core.request('loudness.run',{previewId:again.previewId,confirmed:true});assert.equal(cached.changedCount,0);assert.equal(cached.backupCount,0);assert.equal(cached.unchangedCount,1);
  // Standalone bridge fixtures must meet the same canonical-data-root invariant as Electron storage.
  const aliasTarget=path.join(data,'alias-target'),alias=path.join(data,'data-alias'),aliasMusic=path.join(data,'alias-music');await mkdir(aliasTarget);await mkdir(aliasMusic);await symlink(aliasTarget,alias,'dir');const aliasAudio=path.join(aliasMusic,'fresh.flac');await writeFile(aliasAudio,before);const sentinel=path.join(aliasTarget,'sentinel.bin'),sentinelBytes=Buffer.from('untouched alias target');await writeFile(sentinel,sentinelBytes);const targetEntries=await readdir(aliasTarget);
  const aliased=new PythonBridge(python,['-m','xfinaudio.headless','--data-dir',alias],{...process.env,PYTHONPATH:path.join(root,'src')});
  // Recovery now rejects aliased storage before opening repositories, rather than waiting for writeback.
  try{await assert.rejects(aliased.request('library.scan',{root:aliasMusic}),/(?:core stopped|core unavailable|EPIPE)/i);}finally{await aliased.close();}
  assert.deepEqual(await readdir(aliasTarget),targetEntries);assert.deepEqual(await readFile(sentinel),sentinelBytes);assert.deepEqual(await readFile(aliasAudio),before);
  assert.deepEqual(await readFile(source),sourceBefore);
 }finally{await core.close();await rm(data,{recursive:true,force:true});}
});
