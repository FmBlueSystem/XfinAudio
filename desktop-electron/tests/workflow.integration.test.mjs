import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,realpath,rm,readFile,cp,unlink} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const require=createRequire(import.meta.url);
const {PythonBridge}=require('../.out/main/bridge.js');
const {audioResponse}=require('../.out/main/audio.js');
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const music=path.join(root,'desktop-electron/tests/fixtures/music');
const python=process.env.XFIN_PYTHON;
test('real Qt-free core scans FLAC, generates balanced, saves/reopens and serves seek bytes', {skip:!python},async()=>{
 const data=await realpath(await mkdtemp('/tmp/xfin-integrated-'));
 const start=()=>new PythonBridge(python,['-m','xfinaudio.headless','--data-dir',data],{...process.env,PYTHONPATH:path.join(root,'src')});
 let core=start();
 try{
  let progress=0;core.on('progress',()=>progress++);
  const scanned=await core.request('library.scan',{root:music});assert.equal(scanned.tracks.length,8);assert.ok(progress>0);
  const review=await core.request('prep.generate',{targetTrackCount:4,name:'Integration'});assert.equal(review.variant,'balanced');assert.ok(review.tracks.length>=2);assert.ok(review.reviewId);
  const saved=await core.request('playlist.save',{name:'Integration',reviewId:review.reviewId});assert.equal(saved.trackCount,review.tracks.length);
  const source=await core.request('track.resolve',{trackId:review.tracks[0].id});
  const before=createHash('sha256').update(await readFile(source.path)).digest('hex');
  const response=await audioResponse(new Request(`xfin-audio://track/${review.tracks[0].id}`,{headers:{range:'bytes=0-3'}}),id=>core.request('track.resolve',{trackId:id}));assert.equal(response.status,206);assert.equal(await response.text(),'fLaC');
  await core.close();core=start();const reopened=await core.request('playlist.open',{playlistId:saved.id});assert.deepEqual(reopened.tracks.map(t=>t.id),review.tracks.map(t=>t.id));
  assert.equal(createHash('sha256').update(await readFile(source.path)).digest('hex'),before);
 }finally{await core.close();await rm(data,{recursive:true});}
});
test('real catalog, full intent, fresh variant review and metadata report stay Qt-free',{skip:!python},async()=>{
 const data=await realpath(await mkdtemp('/tmp/xfin-intent-'));
 const core=new PythonBridge(python,['-m','xfinaudio.headless','--data-dir',data],{...process.env,PYTHONPATH:path.join(root,'src')});
 try{
  const scanned=await core.request('library.scan',{root:music});
  const catalog=await core.request('prep.catalog');assert.equal(catalog.strategies.length,11);assert.ok(catalog.strategies.some(item=>item.name==='warmup'));
  const opening=scanned.tracks[0].id,excluded=scanned.tracks.at(-1).id;
  const review=await core.request('prep.generate',{targetTrackCount:4,name:'Warmup',strategy:'warmup',genreFocus:'House',startTrackId:opening,excludedTrackIds:[excluded]});
  assert.deepEqual(review.variants.map(item=>item.name),['safe','balanced','adventurous']);assert.ok(review.planId);assert.equal(review.tracks[0].id,opening);assert.ok(review.tracks.every(item=>item.id!==excluded));
  const selected=await core.request('prep.select',{planId:review.planId,variant:'safe'});assert.equal(selected.variant,'safe');assert.notEqual(selected.reviewId,review.reviewId);
  await assert.rejects(core.request('playlist.save',{name:'stale',reviewId:review.reviewId}));
  const report=await core.request('metadata.report');assert.equal(report.totalTracks,8);assert.equal(report.incompleteCount,0);assert.equal(report.readOnly,true);assert.equal(JSON.stringify(report).includes(music),false);
  const saved=await core.request('playlist.save',{name:'Safe warmup',reviewId:selected.reviewId});assert.equal(saved.trackCount,selected.tracks.length);
 }finally{await core.close();await rm(data,{recursive:true});}
});

test('real saved editor previews without writes, commits atomically and recovers stale/missing snapshots',{skip:!python},async()=>{
 const data=await realpath(await mkdtemp('/tmp/xfin-editor-'));const copied=path.join(data,'music');await cp(music,copied,{recursive:true});
 const core=new PythonBridge(python,['-m','xfinaudio.headless','--data-dir',data],{...process.env,PYTHONPATH:path.join(root,'src')});
 try{
  await core.request('library.scan',{root:copied});const review=await core.request('prep.generate',{targetTrackCount:4,name:'Original'});
  const original=await core.request('playlist.save',{name:'Original',reviewId:review.reviewId});
  const renamed=await core.request('playlist.rename',{playlistId:original.id,name:'Renamed original'});assert.equal(renamed.name,'Renamed original');
  const duplicate=await core.request('playlist.duplicate',{playlistId:original.id});assert.notEqual(duplicate.id,original.id);assert.equal(duplicate.trackCount,4);
  const edit=await core.request('playlist.edit.open',{playlistId:duplicate.id});const order=edit.tracks.map(track=>track.id).reverse();
  const proposal=await core.request('playlist.edit.preview',{editId:edit.editId,trackIds:order,request:'acorta a 2 temas'});assert.equal(proposal.tracks.length,2);assert.ok(proposal.assessment.description);
  assert.equal((await core.request('playlist.open',{playlistId:duplicate.id})).tracks.length,4);
  const saved=await core.request('playlist.edit.save',{editId:edit.editId,name:'Edited copy',trackIds:proposal.tracks.map(track=>track.id)});assert.equal(saved.tracks.length,2);assert.notEqual(saved.editId,edit.editId);
  assert.equal((await core.request('playlist.open',{playlistId:original.id})).tracks.length,4);
  await core.request('playlist.rename',{playlistId:duplicate.id,name:'Changed elsewhere'});
  await assert.rejects(core.request('playlist.edit.save',{editId:saved.editId,name:'Must not overwrite',trackIds:order}),error=>error.code==='stale_edit');
  const refreshed=await core.request('playlist.edit.discard',{editId:saved.editId});assert.equal(refreshed.name,'Changed elsewhere');assert.equal(refreshed.tracks.length,2);
  const source=await core.request('track.resolve',{trackId:refreshed.tracks[0].id});await unlink(source.path);
  const missing=await core.request('playlist.edit.open',{playlistId:duplicate.id});assert.equal(missing.tracks.length,2);assert.equal(missing.missingTrackCount,1);
  const preserved=await core.request('playlist.edit.save',{editId:missing.editId,name:missing.name,trackIds:missing.tracks.map(track=>track.id)});assert.equal(preserved.missingTrackCount,1);assert.equal(preserved.tracks.length,2);
  await core.request('library.scan',{root:copied});await assert.rejects(core.request('playlist.edit.discard',{editId:preserved.editId}),error=>error.code==='stale_edit');
  const reopened=await core.request('playlist.edit.open',{playlistId:duplicate.id});assert.ok(reopened.editId);
 }finally{await core.close();await rm(data,{recursive:true});}
});
test('real preferences persist with authorized multi-root rescan and no audio mutation',{skip:!python},async()=>{
 const {mkdir,readdir}=await import('node:fs/promises');const data=await realpath(await mkdtemp('/tmp/xfin-preferences-')),first=path.join(data,'music-one'),second=path.join(data,'music-two');await mkdir(first);await mkdir(second);const names=(await readdir(music)).filter(name=>name.endsWith('.flac'));await cp(path.join(music,names[0]),path.join(first,names[0]));await cp(path.join(music,names[1]),path.join(second,names[1]));
 const hash=async()=>Promise.all([path.join(first,names[0]),path.join(second,names[1])].map(async file=>createHash('sha256').update(await readFile(file)).digest('hex'))),before=await hash();
 const start=()=>new PythonBridge(python,['-m','xfinaudio.headless','--data-dir',data],{...process.env,PYTHONPATH:path.join(root,'src')});let core=start();
 try{const settings=await core.request('settings.get');assert.equal(settings.previewVolume,0.7);assert.equal(settings.capabilities.loudnessWriteback,true);await core.request('settings.update',{revision:settings.revision,previewVolume:0.23,watchLibrary:false});await core.request('library.scan',{root:first});await core.request('library.scan',{root:second});await core.close();core=start();const restored=await core.request('settings.get');assert.equal(restored.previewVolume,0.23);assert.equal(restored.watchLibrary,false);assert.equal(restored.libraryLabels.length,2);assert.equal((await core.request('library.rescan')).tracks.length,2);await assert.rejects(core.request('library.rescan',{root:'/private'}),error=>error.code==='invalid_params');assert.deepEqual(await hash(),before);}finally{await core.close();await rm(data,{recursive:true});}
});
test('improvement save bridge routes only to its dedicated bound command and keeps manual editing unchanged',async()=>{
 const main=await readFile(new URL('../src/main.ts',import.meta.url),'utf8'),preload=await readFile(new URL('../src/preload.ts',import.meta.url),'utf8');
 assert.ok(preload.includes("savePlaylistImprovement:(params:unknown)=>invoke('savePlaylistImprovement',params)"),'the bridge must expose only the opaque improvement save params');
 assert.equal((main.match(/playlist\.edit\.save_improvement/g)??[]).length,1,'exactly one command may reach the improvement save');
 assert.match(main,/case 'savePlaylistImprovement':return editSnapshot\(await run\('playlist\.edit\.save_improvement',params\)\);/,'the improvement save must route through the shared host request');
 assert.match(main,/case 'previewPlaylistEdit':return run\('playlist\.edit\.preview',params\);/,'the manual preview command must stay unchanged');
 assert.match(main,/case 'savePlaylistEdit':return editSnapshot\(await run\('playlist\.edit\.save',params\)\);/,'the manual save command must stay unchanged');
 assert.match(main,/case 'discardPlaylistEdit':return editSnapshot\(await run\('playlist\.edit\.discard',params\)\);/,'the manual discard command must stay unchanged');
});
