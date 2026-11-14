import assert from 'node:assert/strict';
import test from 'node:test';
import {createRequire} from 'node:module';
import {mkdir,mkdtemp,readFile,readdir,realpath,rm,symlink,writeFile} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
const require=createRequire(import.meta.url);
const {LOG_FILE_NAME,RotatingLog,revealLogFolder}=require('../.out/main/log-file.js');
const {validateRequest}=require('../.out/main/security.js');
const scratch=async(context)=>{const root=await realpath(await mkdtemp(path.join(os.tmpdir(),'xfin-log-')));context.after(()=>rm(root,{recursive:true,force:true}));return root;};
const stamp=/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z /;
test('the support log rotates inside a size bound under the app data directory',async(context)=>{
  const root=await scratch(context),directory=path.join(root,'logs');
  const log=new RotatingLog(directory,{maxBytes:400});
  for(let index=0;index<40;index+=1)log.write(`line ${index} ${'x'.repeat(40)}`);
  await log.flush();
  const files=(await readdir(directory)).sort();
  assert.deepEqual(files,[LOG_FILE_NAME,`${LOG_FILE_NAME}.1`],'only the current log and one rotated generation exist');
  for(const file of files){
    const text=await readFile(path.join(directory,file),'utf8');
    assert.ok(Buffer.byteLength(text)<=1200,`${file} stays inside the size bound`);
    for(const line of text.split('\n').filter(Boolean)){
      assert.match(line,stamp,`${file} timestamps every entry`);
      assert.match(line,/line \d+ x+$/,`${file} holds one bounded entry per line`);
    }
  }
  assert.match(await readFile(path.join(directory,LOG_FILE_NAME),'utf8'),/line 39 /,'the newest entry is in the current file');
  assert.doesNotMatch(await readFile(path.join(directory,`${LOG_FILE_NAME}.1`),'utf8'),/line 0 /,'rotation discards the oldest history');
});
test('one write is one line and an unusable log path never breaks the caller',async(context)=>{
  const root=await scratch(context),directory=path.join(root,'logs');
  const log=new RotatingLog(directory);
  log.write('first\n2026-01-01T00:00:00.000Z forged entry');
  await log.flush();
  const lines=(await readFile(path.join(directory,LOG_FILE_NAME),'utf8')).split('\n').filter(Boolean);
  assert.equal(lines.length,1,'a multi-line message cannot forge extra entries');
  assert.match(lines[0],/first 2026-01-01T00:00:00\.000Z forged entry$/);
  const blocked=path.join(root,'not-a-directory');
  await writeFile(blocked,'x');
  const broken=new RotatingLog(blocked);
  broken.write('dropped');
  await broken.flush();
  const nested=path.join(root,'nested','logs'),created=new RotatingLog(nested);
  created.write('created');
  await created.flush();
  assert.match(await readFile(path.join(nested,LOG_FILE_NAME),'utf8'),/created/,'the log directory is created on demand');
});
test('the reveal action only opens the fixed app data folder and is allowlisted',async(context)=>{
  const root=await scratch(context),data=path.join(root,'data'),outside=path.join(root,'outside');
  await mkdir(data);
  await mkdir(outside);
  const seen=[];
  assert.deepEqual(await revealLogFolder(data,(filename)=>seen.push(filename)),{found:false});
  const folder=path.join(data,'logs');
  await mkdir(folder);
  assert.deepEqual(await revealLogFolder(data,(filename)=>seen.push(filename)),{found:true});
  assert.deepEqual(seen,[folder]);
  await rm(folder,{recursive:true});
  await symlink(outside,folder);
  await assert.rejects(revealLogFolder(data,(filename)=>seen.push(filename)),/logs_unavailable/);
  assert.equal(seen.length,1,'a redirected log folder is never revealed');
  assert.deepEqual(validateRequest('revealLogs'),{});
  assert.throws(()=>validateRequest('revealLogs',{path:outside}));
});
