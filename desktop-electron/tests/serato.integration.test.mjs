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
  // S1: every export is nested under the `XfinAudio` parent crate, which is created once as the
  // empty crate (the same version TLV record, no track records) and never rewritten. A saved
  // playlist export therefore leaves two files in `Subcrates`: the parent and the nested crate.
  const tlv=(tag,payload)=>{const head=Buffer.alloc(8);head.write(tag,0,'latin1');head.writeUInt32BE(payload.length,4);return Buffer.concat([head,payload]);};
  const emptyCrate=tlv('vrsn',Buffer.from('1.0/Serato ScratchLive Crate','utf16le').swap16());
  const subcrates=path.join(destination,'Subcrates'),parent=path.join(subcrates,'XfinAudio.crate');
  const listing=async()=>(await readdir(subcrates)).sort();
  const preview=await host.preview(input);assert.equal(preview.canCommit,true);assert.equal(preview.trackCount,review.tracks.length);assert.deepEqual(await listing(),[]);assert.equal(JSON.stringify(preview).includes(temp),false);
  assert.deepEqual(preview.parentsToCreate,['XfinAudio'],'the preview names the missing XfinAudio parent crate it will create');
  assert.deepEqual(await host.commit(preview.previewId),{cancelled:true});assert.deepEqual(await listing(),[]);
  consent=true;const receipt=await host.commit(preview.previewId);assert.equal(receipt.validated,true);assert.equal(receipt.backupCreated,false);assert.equal(dialogs,2);
  assert.equal(receipt.filename,'XfinAudio%%Serato fixture.crate','a saved playlist export is nested under the XfinAudio parent crate');
  assert.deepEqual(receipt.parentsCreated,['XfinAudio'],'the first export creates the XfinAudio parent crate');
  const target=path.join(subcrates,receipt.filename),first=await readFile(target);
  assert.equal(path.dirname(target),subcrates,'the crate lands in the fixture Subcrates folder');
  assert.ok(target.startsWith(temp+path.sep),'the crate lands inside the temporary fixture');
  assert.deepEqual(await readFile(parent),emptyCrate,'the parent crate is created empty, not as a copy of the export');
  await host.reveal(receipt.receiptId);assert.deepEqual(shown,[target],'the receipt resolves to the exported crate, not to its parent');
  assert.deepEqual(await host.commit(preview.previewId),receipt);assert.deepEqual(await listing(),[receipt.filename,'XfinAudio.crate'].sort());
  const replacement=await host.preview(input);assert.equal(replacement.backup.required,true);
  assert.deepEqual(replacement.parentsToCreate,[],'an existing parent crate is never created again');
  const updated=await host.commit(replacement.previewId);assert.equal(updated.backupCreated,true);assert.equal(updated.validated,true);
  assert.deepEqual(updated.parentsCreated,[],'the replace never rewrites the parent crate');
  const entries=await listing(),backup=entries.find(name=>name.includes('.bak'));assert.ok(backup);
  assert.deepEqual(await readFile(path.join(subcrates,backup)),first);
  assert.equal(backup,receipt.filename+'.bak','the replace backs up the nested crate only');
  assert.deepEqual(entries,[receipt.filename,receipt.filename+'.bak','XfinAudio.crate'].sort(),'the parent crate is neither replaced nor backed up');
  assert.deepEqual(await readFile(parent),emptyCrate,'the parent crate keeps its exact empty content');
  const stale=await host.preview(input);await core.request('playlist.rename',{playlistId:saved.id,name:'Changed after preview'});await assert.rejects(host.commit(stale.previewId),error=>error.code==='stale_source');
  assert.equal(await readFile(path.join(destination,'database V2'),'utf8'),'DO NOT MODIFY');assert.deepEqual(await Promise.all(files.map(hash)),before);
 }finally{await host.waitForCommit();await core.close();await rm(temp,{recursive:true,force:true});}
});
