import test from 'node:test';import assert from 'node:assert/strict';
import {mkdtemp,mkdir,rm,readFile,writeFile,cp,readdir,realpath} from 'node:fs/promises';
import {createHash} from 'node:crypto';import {createRequire} from 'node:module';import path from 'node:path';import os from 'node:os';import {fileURLToPath} from 'node:url';
const require=createRequire(import.meta.url),{PythonBridge}=require('../.out/main/bridge.js'),{SeratoHost}=require('../.out/main/serato-host.js');
const repo=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..'),python=process.env.XFIN_PYTHON;
const hash=async filename=>createHash('sha256').update(await readFile(filename)).digest('hex');
test('real Qt-free Serato pipeline previews readonly, confirms once, validates backup and preserves source hashes',{skip:!python,timeout:30000},async()=>{
 const temp=await realpath(await mkdtemp(path.join(os.tmpdir(),'xfin-serato-integration-'))),music=path.join(temp,'music'),destination=path.join(temp,'_Serato_'),data=path.join(temp,'data');
 // S3: the core discovers `_Serato_` folders by itself, and `~/Music/_Serato_` used to win over
 // this fixture on a machine that has one. The core process runs with HOME inside the fixture,
 // and no other folder may ever reach registration.
 assert.ok(destination.startsWith(temp+path.sep),'the fixture destination lives inside the temporary directory');
 await cp(path.join(repo,'desktop-electron/tests/fixtures/music'),music,{recursive:true});await mkdir(path.join(destination,'Subcrates'),{recursive:true});await writeFile(path.join(destination,'database V2'),'DO NOT MODIFY');
 const files=(await readdir(music)).map(name=>path.join(music,name)),before=await Promise.all(files.map(hash));
 const core=new PythonBridge(python,['-m','xfinaudio.headless','--data-dir',data],{...process.env,PYTHONPATH:path.join(repo,'src'),HOME:temp});
 let consent=false,dialogs=0;const shown=[],suggestions=[];
 const request=async(method,params)=>{
  if(method!=='serato.suggestDestination')return core.request(method,params);
  // Record what the core's own discovery answers, then let the host use this test's folder:
  // nothing but the fixture can be the destination of this run.
  const answer=await core.request(method,params);suggestions.push(answer.suggestion??null);return {suggestion:null};
 };
 const host=new SeratoHost({request,choose:async()=>destination,confirm:async()=>{dialogs++;return consent;},reveal:filename=>shown.push(filename),isClosing:()=>false});
 try {
  const scan=await core.request('library.scan',{root:music});assert.equal(scan.tracks.length,8);
  const review=await core.request('prep.generate',{targetTrackCount:4,name:'Serato fixture'});const saved=await core.request('playlist.save',{reviewId:review.reviewId,name:'Serato fixture'});
  const dest=await host.choose(),input={source:{kind:'saved',playlistId:String(saved.id)},destinationId:dest.destinationId,name:'Serato fixture'};
  assert.equal(suggestions.length,1,'one destination choice asks the core once');
  assert.ok(suggestions[0]===null||suggestions[0].startsWith(temp+path.sep),`the core never proposes an _Serato_ folder outside the fixture (got ${suggestions[0]})`);
  const preview=await host.preview(input);assert.equal(preview.canCommit,true);assert.equal(preview.trackCount,review.tracks.length);assert.deepEqual(await readdir(path.join(destination,'Subcrates')),[]);assert.equal(JSON.stringify(preview).includes(temp),false);
  assert.deepEqual(await host.commit(preview.previewId),{cancelled:true});assert.deepEqual(await readdir(path.join(destination,'Subcrates')),[]);
  consent=true;const receipt=await host.commit(preview.previewId);assert.equal(receipt.validated,true);assert.equal(receipt.backupCreated,false);assert.equal(dialogs,2);
  const target=path.join(destination,'Subcrates',receipt.filename),first=await readFile(target);
  assert.equal(path.dirname(target),path.join(destination,'Subcrates'),'the crate lands in the fixture Subcrates folder');
  assert.ok(target.startsWith(temp+path.sep),'the crate lands inside the temporary fixture');
  await host.reveal(receipt.receiptId);assert.deepEqual(shown,[target]);
  assert.deepEqual(await host.commit(preview.previewId),receipt);assert.deepEqual(await readdir(path.dirname(target)),[receipt.filename]);
  const replacement=await host.preview(input);assert.equal(replacement.backup.required,true);const updated=await host.commit(replacement.previewId);assert.equal(updated.backupCreated,true);assert.equal(updated.validated,true);
  const entries=await readdir(path.dirname(target)),backup=entries.find(name=>name.includes('.bak'));assert.ok(backup);assert.deepEqual(await readFile(path.join(path.dirname(target),backup)),first);
  const stale=await host.preview(input);await core.request('playlist.rename',{playlistId:saved.id,name:'Changed after preview'});await assert.rejects(host.commit(stale.previewId),error=>error.code==='stale_source');
  assert.equal(await readFile(path.join(destination,'database V2'),'utf8'),'DO NOT MODIFY');assert.deepEqual(await Promise.all(files.map(hash)),before);
 }finally{await host.waitForCommit();await core.close();await rm(temp,{recursive:true,force:true});}
});
