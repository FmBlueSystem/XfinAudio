import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,realpath,stat,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createRequire} from 'node:module';
import {readFile} from 'node:fs/promises';
const require=createRequire(import.meta.url);
const {configureStorage}=require('../.out/main/storage.js');
test('Chromium profile, session, logs and crash paths are confined to chosen data root',async()=>{
 const root=await mkdtemp(join(tmpdir(),'xfin-storage-'));const paths={};
 const app={isPackaged:false,getPath:()=>{throw new Error('Default profile must not be used');},setPath:(name,value)=>{paths[name]=value;}};
 try{
  const chosen=configureStorage(app,root);assert.equal(chosen,await realpath(root));
  for(const name of ['userData','sessionData','logs','crashDumps']){assert.ok(paths[name].startsWith(chosen+'/'));assert.equal((await stat(paths[name])).isDirectory(),true);}
  assert.throws(()=>configureStorage(app,'relative/path'));
 }finally{await rm(root,{recursive:true});}
});
test('storage isolation is configured synchronously before Electron readiness',async()=>{
 const main=await readFile(new URL('../src/main.ts',import.meta.url),'utf8');
 assert.ok(main.indexOf('configureStorage(app')>=0);
 assert.ok(main.indexOf('configureStorage(app')<main.indexOf('app.whenReady()'));
 assert.equal(main.includes("const dataDir=app.isPackaged?app.getPath('userData')"),false);
});
