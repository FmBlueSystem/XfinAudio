import test from 'node:test';import assert from 'node:assert/strict';import {createRequire} from 'node:module';import {mkdtemp,mkdir,writeFile,symlink,rm,realpath} from 'node:fs/promises';import os from 'node:os';import path from 'node:path';
const require=createRequire(import.meta.url),{createNativeWatchFactory}=require('../.out/main/native-watch.js');
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function until(predicate){const end=Date.now()+5000;while(!predicate()){if(Date.now()>end)throw new Error('Watcher did not reach expected state');await wait(20);}}
test('real native watcher detects authorized nested changes, ignores app data and awaits thread exit',{timeout:12000},async()=>{
 const root=await realpath(await mkdtemp(path.join(os.tmpdir(),'xfin-watch-'))),music=path.join(root,'music'),ignore=path.join(music,'owned');await mkdir(ignore,{recursive:true});await mkdir(path.join(music,'album'));
 let ready=null;const changed=[];const failed=[];const driver=createNativeWatchFactory(ignore)([music],{ready:roots=>{ready=roots;},change:r=>changed.push(r),failed:r=>failed.push(r)});
 try {await until(()=>ready!==null);assert.deepEqual(ready,[music]);await writeFile(path.join(ignore,'settings.json'),'{}');await wait(300);assert.deepEqual(changed,[]);await writeFile(path.join(music,'album','new.flac'),'fixture');await until(()=>changed.length>0);assert.ok(changed.every(r=>r===music));assert.deepEqual(failed,[]);await driver.close();const count=changed.length;await writeFile(path.join(music,'album','later.flac'),'fixture');await wait(150);assert.equal(changed.length,count);}finally{await driver.close();await rm(root,{recursive:true,force:true});}
});
test('linked or unavailable trees fail closed without watching external sources',{timeout:12000},async()=>{
 const root=await realpath(await mkdtemp(path.join(os.tmpdir(),'xfin-watch-links-'))),music=path.join(root,'music'),outside=path.join(root,'outside');await mkdir(music);await mkdir(outside);await writeFile(path.join(outside,'private.flac'),'fixture');await symlink(outside,path.join(music,'link'));
 let ready=null;const changed=[];const failed=[];const driver=createNativeWatchFactory(path.join(root,'data'))([music,path.join(root,'missing')],{ready:roots=>{ready=roots;},change:r=>changed.push(r),failed:r=>failed.push(r)});
 try{await until(()=>ready!==null);assert.deepEqual(ready,[]);assert.equal(failed.length,2);await writeFile(path.join(outside,'private.flac'),'changed');await wait(200);assert.deepEqual(changed,[]);}finally{await driver.close();await rm(root,{recursive:true,force:true});}
});
test('new and replaced directory identities receive fresh watches',{timeout:12000},async()=>{
 const {rename}=await import('node:fs/promises');const root=await realpath(await mkdtemp(path.join(os.tmpdir(),'xfin-watch-refresh-'))),music=path.join(root,'music'),album=path.join(music,'album');await mkdir(album,{recursive:true});
 let ready=false,count=0;const failed=[];const driver=createNativeWatchFactory(path.join(root,'data'))([music],{ready:()=>{ready=true;},change:()=>count++,failed:r=>failed.push(r)});
 try{await until(()=>ready);await rename(album,path.join(root,'retired'));await mkdir(album);await until(()=>count>0);const previous=count;await writeFile(path.join(album,'fresh.flac'),'fixture');await until(()=>count>previous);assert.deepEqual(failed,[]);const newDir=path.join(music,'new');await mkdir(newDir);await wait(200);const before=count;await writeFile(path.join(newDir,'new.flac'),'fixture');await until(()=>count>before);}finally{await driver.close();await rm(root,{recursive:true,force:true});}
});
test('short owned-write suppression is exact-path, expires, and never masks another file',{timeout:12000},async()=>{
 const root=await realpath(await mkdtemp(path.join(os.tmpdir(),'xfin-watch-suppress-'))),music=path.join(root,'music');await mkdir(music);const owned=path.join(music,'owned.flac'),other=path.join(music,'other.flac');await writeFile(owned,'fixture');await writeFile(other,'fixture');
 let ready=false,count=0;const driver=createNativeWatchFactory(path.join(root,'data'))([music],{ready:()=>ready=true,change:()=>count++,failed:()=>{}});
 try{await until(()=>ready);driver.suppress([owned],500);await writeFile(owned,'app metadata');await wait(220);assert.equal(count,0);await writeFile(other,'external metadata');await until(()=>count>0);await wait(400);const previous=count;await writeFile(owned,'later external metadata');await until(()=>count>previous);}finally{await driver.close();await rm(root,{recursive:true,force:true});}
});
